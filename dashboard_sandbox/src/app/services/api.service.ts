import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable, throwError } from 'rxjs';
import { tap, catchError } from 'rxjs/operators';

@Injectable({ providedIn: 'root' })
export class ApiService {
  private apiUrl = 'http://localhost:5000'; // Adresse de ton back-end Flask

  constructor(private http: HttpClient) {}

  // =====================================================================
  // METHODES GENERIQUES
  // =====================================================================

  private getHeaders(): HttpHeaders {
    return new HttpHeaders({
      'Content-Type': 'application/json',
      'Accept': 'application/json'
    });
  }

  // =====================================================================
  // UPLOAD & ANALYSE
  // =====================================================================

  uploadFile(formData: FormData): Observable<any> {
    return this.http.post(`${this.apiUrl}/upload`, formData);
  }

  analyzeFile(payload: { filename: string, tache: string, domaine: string }): Observable<any> {
    return this.http.post(`${this.apiUrl}/analyze`, JSON.stringify(payload), { headers: this.getHeaders() }).pipe(
      tap(response => console.log('Analyse réussie :', response)),
      catchError(error => {
        console.error('Erreur lors de l\'analyse :', error);
        return throwError(() => error);
      })
    );
  }

  // Analyse par ticker yfinance
  analyzeTicker(ticker: string): Observable<any> {
    return this.http.post(
      `${this.apiUrl}/analyze-ticker`,
      { ticker: ticker },
      { headers: this.getHeaders() }
    );
  }

  // =====================================================================
  // SIMULATION
  // =====================================================================

  simulate(data: any, plugin: string): Observable<any> {
    return this.http.post(`${this.apiUrl}/simulate`, {
      data,
      plugin
    });
  }

  // =====================================================================
  // LOGISTIQUE - SCHEDULING (NOUVEL API)
  // =====================================================================

  /**
   * Planification principale avec heuristiques + recuit simulé
   * @param tasks - Liste des tâches
   * @param numMachines - Nombre de machines
   * @param rule - Règle heuristique (SPT, EDD, LPT, WSPT)
   * @param saConfig - Configuration du recuit simulé
   * @param enableSA - Activer l'optimisation SA
   */
  schedule(tasks: any[], numMachines: number = 3, rule: string = 'EDD', saConfig?: any, enableSA: boolean = true): Observable<any> {
    const payload = {
      tasks: tasks,
      num_machines: numMachines,
      rule: rule,
      sa_config: saConfig,
      enable_sa: enableSA
    };

    return this.http.post(`${this.apiUrl}/schedule`, payload, { headers: this.getHeaders() }).pipe(
      tap(response => console.log('Scheduling réussi :', response)),
      catchError(error => {
        console.error('Erreur de scheduling :', error);
        return throwError(() => error);
      })
    );
  }

  /**
   * Liste les règles heuristiques disponibles
   */
  getScheduleRules(): Observable<any> {
    return this.http.get(`${this.apiUrl}/schedule/rules`);
  }

  /**
   * Historique des ordonnancements
   */
  getScheduleHistory(): Observable<any> {
    return this.http.get(`${this.apiUrl}/schedule/history`);
  }

  /**
   * Compare deux sessions d'ordonnancement
   */
  compareSchedules(sessionId1: number, sessionId2: number): Observable<any> {
    return this.http.get(`${this.apiUrl}/schedule/compare/${sessionId1}/${sessionId2}`);
  }

  /**
   * Simulation what-if
   */
  scheduleSimulate(scenario: any): Observable<any> {
    return this.http.post(`${this.apiUrl}/schedule/simulate`, scenario, { headers: this.getHeaders() });
  }

  // =====================================================================
  // DASHBOARD DATA
  // =====================================================================

  getDashboardData(): Observable<any> {
    return this.http.get(`${this.apiUrl}/dashboard-data`);
  }

  // =====================================================================
  // ANALYSES HISTORY
  // =====================================================================

  getAnalyses(): Observable<any> {
    return this.http.get(`${this.apiUrl}/analyses`);
  }

  getAnalysis(id: number): Observable<any> {
    return this.http.get(`${this.apiUrl}/analyses/${id}`);
  }
}