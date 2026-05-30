import { Component, OnInit } from '@angular/core';
import { MatSnackBar } from '@angular/material/snack-bar';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';

import { ApiService } from '../services/api.service';

interface Domain {
  name: string;
  value: string;
}

@Component({
  selector: 'app-analyze',
  templateUrl: './analyze.component.html',
  styleUrls: ['./analyze.component.css']
})
export class AnalyzeComponent implements OnInit {
  domains: Domain[] = [
    { name: 'Finance', value: 'finance' },
    { name: 'Logistique', value: 'logistic' }
  ];

  selectedDomain: string | null = null;
  file: File | null = null;
  fileName = '';
  isLoading = false;
  error = '';

  analysisResult: {
    roic: number;
    niveau: string;
    commentaire: string;
    interpretation_ia: string;
  } | null = null;

  logisticsResult: {
    assignments: any[];
    makespan: number;
    nb_tasks: number;
    note: string;
  } | null = null;

  constructor(
    private snackBar: MatSnackBar,
    private http: HttpClient,
    private router: Router,
    private apiService: ApiService
  ) {}

  ngOnInit(): void {}

  isFormValid(): boolean {
    return !!this.selectedDomain && !!this.file;
  }

  onFileSelected(event: any): void {
    this.handleFile(event.target.files[0]);
  }

  onDragOver(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
  }

  onFileDrop(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    const files = event.dataTransfer?.files;
    if (files && files.length > 0) {
      this.handleFile(files[0]);
    }
  }

  private handleFile(file: File): void {
    if (this.isValidFileType(file)) {
      this.file = file;
      this.fileName = file.name;
      this.analysisResult = null;
      this.error = '';
    } else {
      this.error = 'Type de fichier non supporté';
      this.snackBar.open(this.error, 'Fermer', { duration: 3000 });
    }
  }

  private isValidFileType(file: File): boolean {
    const allowedTypes = [
      'application/pdf',
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'text/csv'
    ];
    return allowedTypes.includes(file.type);
  }

  analyze(): void {
    if (!this.isFormValid()) return;

    this.isLoading = true;
    this.error = '';

    const formData = new FormData();
    formData.append('file', this.file!);
    console.log('Analyse declenchee');
    console.log('Form valide ?', this.isFormValid());
    console.log('Fichier a uploader :', this.file?.name);
    console.log('Domaine selectionne :', this.selectedDomain);

    this.apiService.uploadFile(formData).subscribe({
      next: () => {
        const payload = {
          filename: this.file!.name,
          tache: 'classification',
          domaine: this.selectedDomain!
        };

        this.apiService.analyzeFile(payload).subscribe({
          next: (response: any) => {
            this.isLoading = false;
            console.log('Reponse backend :', response);

            if (this.selectedDomain === 'finance') {
              this.analysisResult = {
                roic: response.roic,
                niveau: response.niveau,
                commentaire: response.commentaire,
                interpretation_ia: response.interpretation_ia
              };
              this.logisticsResult = null;
            } else if (this.selectedDomain === 'logistic') {
              this.logisticsResult = {
                assignments: response.assignments,
                makespan: response.makespan,
                nb_tasks: response.nb_tasks,
                note: response.note
              };
              this.analysisResult = null;
            }

            this.snackBar.open('Analyse terminee avec succes !', 'Fermer', { duration: 3000 });

            const navigationExtras = {
              queryParams: {
                plugin: this.selectedDomain,
                interpretation: response.interpretation_ia || ''
              },
              state: {
                result: response
              }
            };

            this.router.navigate(['/analyze-result'], navigationExtras);
          },

          error: (err) => {
            this.isLoading = false;
            this.error = 'Erreur pendant l\'analyse.';
            console.error('Erreur analyzeFile :', err);
            // ✅ Apostrophe échappée correctement
            this.snackBar.open('Erreur pendant l\'analyse.', 'Fermer', { duration: 3000 });
          }
        });
      },

      error: (err) => {
        this.isLoading = false;
        this.error = 'Erreur pendant l\'upload du fichier.';
        console.error('Erreur uploadFile :', err);
        // ✅ Apostrophe échappée correctement
        this.snackBar.open('Erreur pendant l\'upload du fichier.', 'Fermer', { duration: 3000 });
      }
    });
  }
}