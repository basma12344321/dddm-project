import { Component, OnInit } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';

@Component({
  selector: 'app-historique',
  templateUrl: './historique.component.html',
  styleUrls: ['./historique.component.css']
})
export class HistoriqueComponent implements OnInit {
  analyses: any[] = [];
  loading = true;

  constructor(private http: HttpClient, private router: Router) {}

  ngOnInit(): void {
    this.http.get<any[]>('http://127.0.0.1:5000/analyses').subscribe({
      next: (data) => {
        this.analyses = data.reverse();
        this.loading = false;
      },
      error: () => { this.loading = false; }
    });
  }

  getNiveauClass(niveau: string): string {
    const map: any = { 'elevee': 'badge-green', 'moyenne': 'badge-orange', 'faible': 'badge-red' };
    return map[niveau] || 'badge-orange';
  }

  formatDate(dateStr: string): string {
    return new Date(dateStr).toLocaleDateString('fr-FR', {
      day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit'
    });
  }
}