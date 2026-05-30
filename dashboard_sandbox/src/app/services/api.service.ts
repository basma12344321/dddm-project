import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable, throwError } from 'rxjs';
import { tap, catchError } from 'rxjs/operators';

@Injectable({ providedIn: 'root' })
export class ApiService {
  private apiUrl = 'http://127.0.0.1:5000'; // Adresse de ton back-end Flask

  constructor(private http: HttpClient) {}

  // 📤 Upload d’un fichier CSV ou PDF
  uploadFile(formData: FormData): Observable<any> {
    return this.http.post(`${this.apiUrl}/upload`, formData);
  }

  // 📊 Analyse d’un fichier (PDF ou CSV)
  analyzeFile(payload: { filename: string, tache: string, domaine: string }): Observable<any> {
    const headers = new HttpHeaders({
      'Content-Type': 'application/json',
      'Accept': 'application/json'
    });
    return this.http.post(`${this.apiUrl}/analyze`, JSON.stringify(payload), { headers }).pipe(
      tap(response => console.log('Analyse réussie :', response)),
      catchError(error => {
        console.error('Erreur lors de l’analyse :', error);
        return throwError(() => error);
      })
    );
  }
  

  // 🧪 Simulation d’un scénario via un plugin
  simulate(data: any, plugin: string): Observable<any> {
    return this.http.post(`${this.apiUrl}/simulate`, {
      data,
      plugin
    });
  }
}