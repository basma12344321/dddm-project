# app/routes/api.py

from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request
import os
import math
import pandas as pd
import traceback
import time
import random
from functools import lru_cache
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from io import BytesIO
import datetime
from app.llm_utils import generate_interpretation
from app.plugins.logistic_plugin import LogisticPlugin


from app.core_engine.core_engine import clean_data
from app.core_engine.plugin_loader import load_plugin
from app.models import db, Analysis, Simulation, SchedulingSession, SchedulingResult, SchedulingSimulation

api_bp = Blueprint('api', __name__)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']


def sanitize_for_json(obj):
    """Remplace NaN et Infinity par None (null en JSON valide)."""
    if isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_for_json(i) for i in obj]
    elif isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    else:
        return obj


def get_current_user_id():
    """Récupère l'ID utilisateur depuis le token JWT si présent."""
    try:
        verify_jwt_in_request(optional=True)
        user_id = get_jwt_identity()
        return int(user_id) if user_id else None
    except Exception:
        return None


@api_bp.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if allowed_file(file.filename):
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], file.filename)
        print(f"Sauvegarde dans : {filepath}")
        try:
            file.save(filepath)
            print("Fichier sauvegarde !")
        except Exception as e:
            print("Erreur pendant la sauvegarde :", e)

        return jsonify({"message": f"Fichier {file.filename} bien recu."}), 200
    else:
        return jsonify({"error": "Format invalide (csv et pdf uniquement)"}), 400


@api_bp.route('/analyze', methods=['POST'])
def analyze():
    print("\n=== Requete /analyze ===")

    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 415

    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Empty JSON body"}), 400

        required_fields = ['filename', 'tache', 'domaine']
        missing_fields = [f for f in required_fields if f not in data]
        if missing_fields:
            return jsonify({"error": "Missing fields", "missing": missing_fields}), 400

        filename = data['filename']
        domaine  = data['domaine']

        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        if not os.path.exists(filepath):
            return jsonify({"error": "Fichier non trouve"}), 404

        filetype = 'pdf' if filename.lower().endswith('.pdf') else 'csv'

        df_raw = clean_data(filepath, filetype=filetype)
        plugin = load_plugin(domaine)

        if domaine == 'logistic':
            raw_result = plugin.schedule(df_raw)
            result = plugin.interpret(raw_result)
        else:
            df_clean    = plugin.preprocess(df_raw)
            prediction  = plugin._make_prediction(df_clean)
            # ✅ Passer df_clean pour le calcul SHAP
            result      = plugin.interpret(prediction, df_clean)

        # Ajouter input_data
        if isinstance(df_raw, pd.DataFrame) and not df_raw.empty:
            try:
                result["input_data"] = sanitize_for_json(df_raw.iloc[0].to_dict())
            except Exception:
                result["input_data"] = {}

        result = sanitize_for_json(result)

        # ✅ Sauvegarder l'analyse dans PostgreSQL
        user_id = get_current_user_id()
        analysis = Analysis(
            user_id     = user_id,
            domain      = domaine,
            plugin_name = domaine,
            filename    = filename,
            result_json = result
        )
        db.session.add(analysis)
        db.session.commit()
        print(f"Analyse sauvegardee en base (id={analysis.id})")

        # Ajouter l'ID de l'analyse dans la réponse
        result["analysis_id"] = analysis.id

        return jsonify(result)

    except Exception as e:
        print("Erreur pendant l'analyse :")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ✅ Ajouter cette route dans backend/app/routes/api.py
# Juste après la route /analyze existante

# Cache simple en mémoire (ticker -> (timestamp, data))
_ticker_cache = {}
CACHE_TTL = 300  # 5 minutes

@api_bp.route('/analyze-ticker', methods=['POST'])
def analyze_ticker():
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 415

    try:
        data   = request.get_json()
        ticker = data.get('ticker', '').strip().upper()

        if not ticker:
            return jsonify({"error": "Ticker manquant"}), 400

        print(f"\n=== Analyse ticker : {ticker} ===")

        # ── Vérifier le cache ─────────────────────────────────────────
        now = time.time()
        if ticker in _ticker_cache:
            cached_time, cached_result = _ticker_cache[ticker]
            if now - cached_time < CACHE_TTL:
                print(f"Cache HIT pour {ticker}")
                return jsonify(cached_result)

        # ── Fetch yfinance avec retry ─────────────────────────────────
        import yfinance as yf

        info = None
        last_error = None

        for attempt in range(3):
            try:
                if attempt > 0:
                    wait = 2 ** attempt + random.uniform(1, 3)
                    print(f"Retry {attempt}/3 pour {ticker} dans {wait:.1f}s...")
                    time.sleep(wait)

                stock = yf.Ticker(ticker)
                info  = stock.info

                if info and len(info) > 10:
                    break
                else:
                    info = None

            except Exception as e:
                last_error = str(e)
                print(f"Tentative {attempt+1} échouée: {last_error}")
                if 'Rate limit' in str(e) or 'Too Many' in str(e):
                    continue
                else:
                    raise

        if not info:
            msg = last_error or f"Données introuvables pour '{ticker}'"
            return jsonify({"error": msg}), 429

        # ── Extraire les données financières ──────────────────────────
        revenue      = info.get('totalRevenue',      0) or 0
        net_income   = info.get('netIncomeToCommon',  0) or 0
        ebitda       = info.get('ebitda',             0) or 0
        total_assets = info.get('totalAssets',        0) or 0
        fcf          = info.get('freeCashflow',       0) or 0
        market_cap   = info.get('marketCap',          0) or 0
        debt_eq      = info.get('debtToEquity',       0) or 0
        gross_profit = info.get('grossProfits',       0) or 0
        op_margins   = info.get('operatingMargins',   0) or 0
        total_debt   = info.get('totalDebt',          0) or 0
        book_value   = info.get('bookValue',          0) or 0
        shares_out   = info.get('sharesOutstanding',  0) or 0
        sector       = info.get('sector',             'Other')
        company_name = info.get('longName',           ticker)

        if revenue == 0:
            return jsonify({"error": f"Données financières insuffisantes pour '{ticker}'"}), 404

        # ── Calcul des indicateurs ────────────────────────────────────
        ebit         = revenue * op_margins if op_margins else ebitda * 0.85
        invested_cap = total_debt + (book_value * shares_out) if shares_out else total_debt
        if invested_cap == 0:
            invested_cap = market_cap * 0.3
        if total_assets == 0:
            total_assets = invested_cap * 1.5

        asset_turnover = revenue / total_assets if total_assets != 0 else 0
        debt_eq_ratio  = debt_eq / 100 if debt_eq > 10 else debt_eq
        sga_to_rev     = max(0, (revenue - gross_profit - ebit) / revenue) if revenue != 0 else 0

        # ── Construire le DataFrame ───────────────────────────────────
        sectors_list = [
            'Consumer Cyclical', 'Consumer Defensive', 'Energy',
            'Healthcare', 'Industrials', 'Technology'
        ]

        data_dict = {
            'EBIT':             [ebit],
            'Invested Capital': [invested_cap],
            'Free Cash Flow':   [fcf],
            'Asset Turnover':   [asset_turnover],
            'Debt to Equity':   [debt_eq_ratio],
            'R&D to Revenue':   [0.0],
            'SG&A to Revenue':  [sga_to_rev],
            'Market Cap':       [market_cap],
        }
        for s in sectors_list:
            data_dict[f'Sector_{s}'] = [1 if sector == s else 0]
        data_dict['Sector_Other'] = [0 if sector in sectors_list else 1]

        expected_cols = [
            'EBIT', 'Invested Capital', 'Free Cash Flow', 'Asset Turnover',
            'Debt to Equity', 'R&D to Revenue', 'SG&A to Revenue', 'Market Cap',
            'Sector_Consumer Cyclical', 'Sector_Consumer Defensive',
            'Sector_Energy', 'Sector_Healthcare',
            'Sector_Industrials', 'Sector_Other', 'Sector_Technology'
        ]

        df_ticker  = pd.DataFrame(data_dict, columns=expected_cols)
        plugin     = load_plugin('finance')
        prediction = plugin._make_prediction(df_ticker)
        result     = plugin.interpret(prediction, df_ticker)

        result['company'] = {
            'ticker':        ticker,
            'name':          company_name,
            'sector':        sector,
            'market_cap':    market_cap,
            'current_price': info.get('currentPrice', 0),
            'currency':      info.get('currency', 'USD'),
            'country':       info.get('country', ''),
        }
        result['financials'] = {
            'revenue':        revenue,
            'net_income':     net_income,
            'ebit':           ebit,
            'fcf':            fcf,
            'market_cap':     market_cap,
            'debt_equity':    debt_eq_ratio,
            'asset_turnover': asset_turnover,
        }

        result = sanitize_for_json(result)

        # ── Mettre en cache ───────────────────────────────────────────
        _ticker_cache[ticker] = (time.time(), result)

        # ── Sauvegarder en base ───────────────────────────────────────
        user_id  = get_current_user_id()
        analysis = Analysis(
            user_id     = user_id,
            domain      = 'finance',
            plugin_name = 'finance',
            filename    = ticker,
            result_json = result
        )
        db.session.add(analysis)
        db.session.commit()
        result['analysis_id'] = analysis.id

        print(f"Analyse ticker {ticker} terminée (ROIC={result['roic']})")
        return jsonify(result)

    except Exception as e:
        print(f"Erreur analyze-ticker: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@api_bp.route('/simulate', methods=['POST'])
def simulate():
    print("Entree dans /simulate")
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 415

    payload = request.get_json(silent=True)
    if payload is None:
        return jsonify({"error": "Invalid JSON"}), 400

    plugin_name = payload.get("plugin")
    analysis_id = payload.get("analysis_id")

    # ✅ Accepter "data" (frontend) ou "params" (ancienne API)
    scenario = payload.get("data") or payload.get("params")

    if not plugin_name:
        return jsonify({"error": "Missing 'plugin'"}), 400
    if not scenario:
        return jsonify({"error": "Missing 'data' or 'params'"}), 400

    try:
        plugin = load_plugin(plugin_name)
        result = plugin.simulate(scenario)
        result = sanitize_for_json(result)

        simulation = Simulation(
            analysis_id     = analysis_id,
            scenario_params = scenario,
            result_json     = result
        )
        db.session.add(simulation)
        db.session.commit()

        result["simulation_id"] = simulation.id
        return jsonify(result)

    except Exception as e:
        print(f"Erreur simulate: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": f"Simulation failed: {str(e)}"}), 500


@api_bp.route('/analyses', methods=['GET'])
def get_analyses():
    """Récupérer l'historique de toutes les analyses."""
    try:
        user_id = get_current_user_id()

        if user_id:
            analyses = Analysis.query.filter_by(user_id=user_id).order_by(
                Analysis.created_at.desc()
            ).all()
        else:
            analyses = Analysis.query.order_by(Analysis.created_at.desc()).limit(50).all()

        return jsonify([a.to_dict() for a in analyses]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route('/analyses/<int:analysis_id>', methods=['GET'])
def get_analysis(analysis_id):
    """Récupérer une analyse spécifique par son ID."""
    analysis = Analysis.query.get(analysis_id)
    if not analysis:
        return jsonify({"error": "Analyse non trouvee"}), 404
    return jsonify(analysis.to_dict()), 200


@api_bp.route("/schedule", methods=["POST"])
def schedule():
    """
    Endpoint principal d'ordonnancement logistique.
    Paramètres:
    - tasks: list de tâches (Task, Duration, Deadline, Priority, Dependencies, SetupTime, MachineConstraint)
    - num_machines: nombre de machines (default: 3)
    - rule: règle heuristique (SPT, EDD, LPT, WSPT)
    - sa_config: config du recuit simulé
    - enable_sa: bool pour activer SA (default: true)
    """
    data = request.get_json()

    if not data:
        return jsonify({"error": "Données JSON manquantes"}), 400

    # Extraire les paramètres
    tasks = data.get('tasks', [])
    num_machines = data.get('num_machines', 3)
    rule = data.get('rule', 'EDD')
    sa_config = data.get('sa_config')
    enable_sa = data.get('enable_sa', True)

    if not tasks:
        return jsonify({"error": "Aucune tâche fournie"}), 400

    if rule not in ['SPT', 'EDD', 'LPT', 'WSPT']:
        return jsonify({"error": f"Règle invalide: {rule}. Options: SPT, EDD, LPT, WSPT"}), 400

    try:
        # Convertir en DataFrame
        df = pd.DataFrame(tasks)

        # Utiliser le plugin logistique
        plugin = load_plugin('logistic')

        # Appeler le moteur d'ordonnancement
        from app.core_engine.scheduling_engine import load_scheduling_engine
        engine = load_scheduling_engine()

        result = engine.schedule(
            data=df,
            num_machines=num_machines,
            rule=rule,
            sa_config=sa_config,
            enable_sa=enable_sa
        )

        # Sauvegarder en base de données
        user_id = get_current_user_id()

        from app.models import SchedulingSession, SchedulingResult

        session = SchedulingSession(
            user_id=user_id,
            num_tasks=len(tasks),
            num_machines=num_machines,
            rule_used=rule,
            execution_time_ms=result.execution_time_ms,
            status=result.status
        )
        db.session.add(session)
        db.session.flush()  # Pour avoir l'ID

        sched_result = SchedulingResult(
            session_id=session.id,
            gantt_data=result.gantt_data,
            metrics=result.metrics,
            interpretation=result.interpretation,
            convergence_data=result.convergence_data
        )
        db.session.add(sched_result)
        db.session.commit()

        # ── Appel LLM ────────────────────────────────────────────────
        try:
            lp = LogisticPlugin()
            prompt = lp._build_llm_prompt(
                result.metrics or {},
                result.interpretation or {},
                len(tasks),
                num_machines
            )
            interpretation_ia = generate_interpretation(prompt)
            print("Interprétation LLM logistique générée avec succès")
        except Exception as llm_err:
            print(f"Avertissement LLM: {llm_err}")
            interpretation_ia = "Interprétation non disponible."

        # Construire la réponse
        response = {
            "status": result.status,
            "execution_time_ms": result.execution_time_ms,
            "gantt_data": result.gantt_data,
            "metrics": result.metrics,
            "optimization_gain": result.optimization_gain,
            "convergence_data": result.convergence_data,
            "interpretation": result.interpretation,
            "interpretation_ia": interpretation_ia,
            "session_id": session.id
        }

        if result.status == "error":
            response["error"] = result.error_message

        return jsonify(sanitize_for_json(response)), 200

    except Exception as e:
        print(f"Erreur schedule: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@api_bp.route("/schedule/rules", methods=["GET"])
def schedule_rules():
    """
    Liste les règles heuristiques disponibles.
    """
    from app.core_engine.scheduling_engine import SchedulingEngine

    rules = []
    for name, description in SchedulingEngine.HEURISTIC_RULES.items():
        rules.append({
            "name": name,
            "description": description
        })

    return jsonify({
        "rules": rules,
        "default": "EDD"
    }), 200


@api_bp.route("/schedule/history", methods=["GET"])
def schedule_history():
    """
    Retourne l'historique des ordonnancements.
    """
    try:
        from app.models import SchedulingSession, SchedulingResult

        user_id = get_current_user_id()

        if user_id:
            sessions = SchedulingSession.query.filter_by(user_id=user_id).order_by(
                SchedulingSession.created_at.desc()
            ).limit(20).all()
        else:
            sessions = SchedulingSession.query.order_by(
                SchedulingSession.created_at.desc()
            ).limit(20).all()

        result = []
        for s in sessions:
            result.append({
                "id": s.id,
                "created_at": s.created_at.isoformat(),
                "num_tasks": s.num_tasks,
                "num_machines": s.num_machines,
                "rule_used": s.rule_used,
                "execution_time_ms": s.execution_time_ms,
                "status": s.status
            })

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/schedule/compare/<int:session_id_1>/<int:session_id_2>", methods=["GET"])
def schedule_compare(session_id_1, session_id_2):
    """
    Compare deux sessions d'ordonnancement.
    """
    try:
        from app.models import SchedulingSession, SchedulingResult

        session1 = SchedulingSession.query.get(session_id_1)
        session2 = SchedulingSession.query.get(session_id_2)

        if not session1 or not session2:
            return jsonify({"error": "Session non trouvée"}), 404

        result1 = SchedulingResult.query.filter_by(session_id=session_id_1).first()
        result2 = SchedulingResult.query.filter_by(session_id=session_id_2).first()

        if not result1 or not result2:
            return jsonify({"error": "Résultat non trouvé"}), 404

        # Calculer les différences
        m1 = result1.metrics or {}
        m2 = result2.metrics or {}

        diff = {
            "makespan_diff": m1.get('makespan', 0) - m2.get('makespan', 0),
            "balance_diff": m1.get('balance_index', 0) - m2.get('balance_index', 0),
            "on_time_rate_diff": m1.get('on_time_rate', 0) - m2.get('on_time_rate', 0),
            "total_tardiness_diff": m1.get('total_tardiness', 0) - m2.get('total_tardiness', 0)
        }

        return jsonify({
            "session1": {
                "id": session_id_1,
                "metrics": m1,
                "rule": session1.rule_used
            },
            "session2": {
                "id": session_id_2,
                "metrics": m2,
                "rule": session2.rule_used
            },
            "diff": diff
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/schedule/simulate", methods=["POST"])
def schedule_simulate():
    """
    Simulation what-if pour le scheduling.
    """
    data = request.get_json()

    if not data:
        return jsonify({"error": "Données JSON manquantes"}), 400

    try:
        plugin = load_plugin('logistic')

        # Appeler simulate avec les paramètres
        result = plugin.simulate(data)

        # Sauvegarder en base
        from app.models import SchedulingSimulation, SchedulingSession

        session_id = data.get('session_id')

        simulation = SchedulingSimulation(
            session_id=session_id,
            scenario_params=data,
            result_json=result,
            diff_metrics=result.get('diff_metrics')
        )
        db.session.add(simulation)
        db.session.commit()

        return jsonify(sanitize_for_json(result)), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route('/dashboard-data', methods=['GET'])
def dashboard_data():
    print("\nRoute /dashboard-data appelee")

    try:
        data_path = os.path.join(current_app.root_path, 'data', 'df_final.csv')
        df = pd.read_csv(data_path)

        if df.empty:
            return jsonify({'error': 'df_final.csv is empty'}), 400
        if 'Sector_Grouped' not in df.columns:
            return jsonify({'error': 'Colonne Sector_Grouped absente'}), 400

        secteur = df['Sector_Grouped'].iloc[0]

        from app.core_engine.model_loader import load_model
        model = load_model('finance', 'regression')

        df_encoded = df.copy()
        if 'ROIC' in df_encoded.columns:
            df_encoded.drop(columns=['ROIC'], inplace=True)

        sector_columns = [
            'Sector_Consumer Cyclical', 'Sector_Consumer Defensive', 'Sector_Energy',
            'Sector_Healthcare', 'Sector_Industrials', 'Sector_Other', 'Sector_Technology'
        ]
        df_encoded = pd.get_dummies(df_encoded, columns=['Sector'], prefix='Sector')

        for col in sector_columns:
            if col not in df_encoded.columns:
                df_encoded[col] = 0

        df_encoded = df_encoded[[
            'EBIT', 'Invested Capital', 'Free Cash Flow', 'Asset Turnover',
            'Debt to Equity', 'R&D to Revenue', 'SG&A to Revenue', 'Market Cap'
        ] + sector_columns]

        y_pred = model.predict(df_encoded)
        df['Predicted_ROIC'] = y_pred

        classement = df[df['Sector_Grouped'] == secteur].sort_values(
            'Predicted_ROIC', ascending=False
        ).reset_index(drop=True)

        top    = classement.head(10)
        labels = [f"Entreprise {i+1}" for i in top.index]
        values = (top["Predicted_ROIC"] * 100).round(1).tolist()

        entreprise      = top.iloc[0]
        secteur_moyenne = classement.mean(numeric_only=True)

        radar_features = [
            'EBIT', 'Invested Capital', 'Free Cash Flow', 'Asset Turnover',
            'Debt to Equity', 'R&D to Revenue', 'SG&A to Revenue', 'Market Cap'
        ]

        radar_data = {
            'labels':     radar_features,
            'entreprise': [round(float(entreprise.get(f, 0)), 2) for f in radar_features],
            'secteur':    [round(float(secteur_moyenne.get(f, 0)), 2) for f in radar_features],
            'titre':      "Comparaison du profil financier (valeurs brutes)"
        }

        response = sanitize_for_json({
            'classement': {
                'labels': labels,
                'values': values,
                'secteur': secteur,
                'titre':  "Top 10 des entreprises du secteur selon le ROIC (%)"
            },
            'radar': radar_data
        })

        return jsonify(response)

    except Exception as e:
        print("Erreur dans /dashboard-data :", str(e))
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@api_bp.route('/export-pdf', methods=['POST'])
def export_pdf():
    try:
        data = request.get_json()
        roic = data.get('roic', 0)
        niveau = data.get('niveau', '')
        commentaire = data.get('commentaire', '')
        interpretation_ia = data.get('interpretation_ia', '')
        shap_data = data.get('shap', {})
        ticker = data.get('ticker', 'Entreprise analysée')

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4,
                                rightMargin=2*cm, leftMargin=2*cm,
                                topMargin=2*cm, bottomMargin=2*cm)

        styles = getSampleStyleSheet()
        elements = []

        # Titre
        title_style = ParagraphStyle('title', parent=styles['Title'],
                                     fontSize=20, textColor=colors.HexColor('#ff4757'),
                                     spaceAfter=6, alignment=TA_CENTER)
        elements.append(Paragraph("SmartDecide — Rapport d'Analyse Financière", title_style))

        # Date
        date_style = ParagraphStyle('date', parent=styles['Normal'],
                                    fontSize=9, textColor=colors.grey, alignment=TA_CENTER)
        elements.append(Paragraph(datetime.datetime.now().strftime("%d/%m/%Y %H:%M"), date_style))
        elements.append(Spacer(1, 0.5*cm))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#ff4757')))
        elements.append(Spacer(1, 0.5*cm))

        # Résumé ROIC
        section_style = ParagraphStyle('section', parent=styles['Heading2'],
                                       fontSize=13, textColor=colors.HexColor('#ff4757'),
                                       spaceBefore=12, spaceAfter=6)
        normal_style = ParagraphStyle('normal', parent=styles['Normal'],
                                      fontSize=10, leading=16, spaceAfter=4)

        elements.append(Paragraph("Résultat de l'analyse", section_style))

        roic_color = '#27ae60' if niveau == 'elevee' else ('#f39c12' if niveau == 'moyenne' else '#e74c3c')
        table_data = [
            ['Indicateur', 'Valeur'],
            ['ROIC prédit', f"{roic*100:.2f}%"],
            ['Niveau de rentabilité', niveau.capitalize()],
            ['Commentaire', commentaire],
        ]
        table = Table(table_data, colWidths=[6*cm, 11*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#ff4757')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#fff5f5')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#fff5f5')]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#ffcccc')),
            ('PADDING', (0, 0), (-1, -1), 8),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 0.5*cm))

        # SHAP
        if shap_data.get('top_features'):
            elements.append(Paragraph("Facteurs clés (SHAP)", section_style))
            shap_table_data = [['Facteur', 'Impact', 'Direction']]
            for f in shap_data['top_features']:
                direction = '↑ Augmente' if f['impact'] == 'positif' else '↓ Diminue'
                shap_table_data.append([f['feature'], f"{f['shap_value']:+.4f}", direction])
            shap_table = Table(shap_table_data, colWidths=[7*cm, 4*cm, 6*cm])
            shap_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#ff4757')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#fff5f5')]),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#ffcccc')),
                ('PADDING', (0, 0), (-1, -1), 7),
            ]))
            elements.append(shap_table)
            elements.append(Spacer(1, 0.5*cm))

        # Rapport LLM
        if interpretation_ia:
            elements.append(Paragraph("Analyse IA — Rapport narratif", section_style))
            for line in interpretation_ia.split('\n'):
                if line.strip():
                    clean = line.replace('**', '').replace('* ', '• ')
                    elements.append(Paragraph(clean, normal_style))

        doc.build(elements)
        buffer.seek(0)

        from flask import send_file
        return send_file(buffer, mimetype='application/pdf',
                         as_attachment=True,
                         download_name=f'rapport_finance_{datetime.datetime.now().strftime("%Y%m%d_%H%M")}.pdf')

    except Exception as e:
        print(f"Erreur export PDF: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/export-pdf-logistic', methods=['POST'])
def export_pdf_logistic():
    try:
        data = request.get_json()
        metrics         = data.get('metrics', {})
        interpretation  = data.get('interpretation', {})
        interpretation_ia = data.get('interpretation_ia', '')
        optimization_gain = data.get('optimization_gain', {})
        gantt_data      = data.get('gantt_data', [])
        num_tasks       = data.get('num_tasks', 0)
        num_machines    = data.get('num_machines', 0)
        rule            = data.get('rule', '')

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4,
                                rightMargin=2*cm, leftMargin=2*cm,
                                topMargin=2*cm, bottomMargin=2*cm)

        styles = getSampleStyleSheet()
        elements = []

        title_style = ParagraphStyle('title', parent=styles['Title'],
                                     fontSize=20, textColor=colors.HexColor('#ff4757'),
                                     spaceAfter=6, alignment=TA_CENTER)
        section_style = ParagraphStyle('section', parent=styles['Heading2'],
                                       fontSize=13, textColor=colors.HexColor('#ff4757'),
                                       spaceBefore=12, spaceAfter=6)
        normal_style = ParagraphStyle('normal', parent=styles['Normal'],
                                      fontSize=10, leading=16, spaceAfter=4)
        date_style = ParagraphStyle('date', parent=styles['Normal'],
                                    fontSize=9, textColor=colors.grey, alignment=TA_CENTER)

        # Titre
        elements.append(Paragraph("SmartDecide — Rapport d'Ordonnancement Logistique", title_style))
        elements.append(Paragraph(datetime.datetime.now().strftime("%d/%m/%Y %H:%M"), date_style))
        elements.append(Spacer(1, 0.4*cm))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#ff4757')))
        elements.append(Spacer(1, 0.4*cm))

        # Paramètres
        elements.append(Paragraph("Paramètres de l'ordonnancement", section_style))
        params_data = [
            ['Paramètre', 'Valeur'],
            ['Nombre de tâches', str(num_tasks)],
            ['Nombre de machines', str(num_machines)],
            ['Règle heuristique', rule],
        ]
        params_table = Table(params_data, colWidths=[6*cm, 11*cm])
        params_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#ff4757')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#fff5f5')]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#ffcccc')),
            ('PADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(params_table)
        elements.append(Spacer(1, 0.4*cm))

        # Métriques
        elements.append(Paragraph("Métriques de performance", section_style))
        on_time = round((metrics.get('on_time_rate', 0) * 100), 1)
        balance = round(metrics.get('balance_index', 0), 2)
        utilization = round(metrics.get('avg_utilization', 0) * 100, 1)
        metrics_data = [
            ['Métrique', 'Valeur'],
            ['Makespan total', f"{metrics.get('makespan', 0)} unités"],
            ['Taux de conformité', f"{on_time}%"],
            ['Index d\'équilibrage', f"{balance} / 1.0"],
            ['Utilisation moyenne', f"{utilization}%"],
            ['Retard total', f"{metrics.get('total_tardiness', 0)} unités"],
        ]
        metrics_table = Table(metrics_data, colWidths=[6*cm, 11*cm])
        metrics_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#ff4757')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#fff5f5')]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#ffcccc')),
            ('PADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(metrics_table)
        elements.append(Spacer(1, 0.4*cm))

        # Gain d'optimisation
        if optimization_gain:
            elements.append(Paragraph("Gain d'optimisation (Recuit Simulé)", section_style))
            gain_data = [
                ['Indicateur', 'Valeur'],
                ['Makespan initial', str(optimization_gain.get('initial_makespan', '—'))],
                ['Makespan optimisé', str(optimization_gain.get('optimized_makespan', '—'))],
                ['Réduction makespan', f"-{optimization_gain.get('makespan_reduction_pct', 0)}%"],
                ['Amélioration équilibrage', f"+{round(optimization_gain.get('balance_improvement', 0)*100, 1)}%"],
            ]
            gain_table = Table(gain_data, colWidths=[6*cm, 11*cm])
            gain_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#ff4757')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#fff5f5')]),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#ffcccc')),
                ('PADDING', (0, 0), (-1, -1), 8),
            ]))
            elements.append(gain_table)
            elements.append(Spacer(1, 0.4*cm))

        # Alertes
        alerts = interpretation.get('alerts', [])
        if alerts:
            elements.append(Paragraph("Alertes", section_style))
            for alert in alerts:
                elements.append(Paragraph(f"⚠ {alert}", normal_style))
            elements.append(Spacer(1, 0.3*cm))

        # Rapport LLM
        if interpretation_ia:
            elements.append(Paragraph("Analyse IA — Rapport narratif", section_style))
            for line in interpretation_ia.split('\n'):
                if line.strip():
                    clean = line.replace('**', '').replace('* ', '• ')
                    elements.append(Paragraph(clean, normal_style))

        doc.build(elements)
        buffer.seek(0)

        from flask import send_file
        return send_file(buffer, mimetype='application/pdf',
                         as_attachment=True,
                         download_name=f'rapport_logistique_{datetime.datetime.now().strftime("%Y%m%d_%H%M")}.pdf')

    except Exception as e:
        print(f"Erreur export PDF logistique: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@api_bp.route('/', methods=['GET'])
def home():
    return "Flask fonctionne parfaitement !"