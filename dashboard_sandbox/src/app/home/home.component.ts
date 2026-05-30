import { Component } from '@angular/core';

@Component({
  selector: 'app-home',
  templateUrl: './home.component.html',
  styleUrls: ['./home.component.css']
})
export class HomeComponent {
  
  onStartAnalysis(): void {
    console.log('Démarrage de l\'analyse');
  }

  onViewDemo(): void {
    console.log('Affichage de la démo');
  }
}