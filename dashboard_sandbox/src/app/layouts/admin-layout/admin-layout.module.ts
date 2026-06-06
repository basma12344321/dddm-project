import { NgModule } from '@angular/core';
import { RouterModule } from '@angular/router';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { AdminLayoutRoutes } from './admin-layout.routing';
import {MatButtonModule} from '@angular/material/button';
import {MatInputModule} from '@angular/material/input';
import {MatRippleModule} from '@angular/material/core';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatTooltipModule} from '@angular/material/tooltip';
import {MatSelectModule} from '@angular/material/select';
import { AnalyzeComponent } from '../../analyze/analyze.component';
import { AnalyzeResultComponent } from '../../analyze-result/analyze-result.component';
import { SimulationComponent } from '../../simulation/simulation.component';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { GanttChartComponent } from '../../components/gantt-chart/gantt-chart.component';
import { LogisticsDashboardComponent } from '../../components/logistics-dashboard/logistics-dashboard.component';
import { MatDividerModule } from '@angular/material/divider';
import { NgApexchartsModule } from "ng-apexcharts";
import { HistoriqueComponent } from '../../historique/historique.component'; // ✅ AJOUT

@NgModule({
  imports: [
    CommonModule,
    RouterModule.forChild(AdminLayoutRoutes),
    FormsModule,
    ReactiveFormsModule,
    MatButtonModule,
    MatRippleModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatTooltipModule,
    MatCardModule,     
    MatIconModule,
    NgApexchartsModule,
    MatDividerModule,
    GanttChartComponent,
    LogisticsDashboardComponent
  ],
  declarations: [
    AnalyzeComponent,
    AnalyzeResultComponent,
    SimulationComponent,
    HistoriqueComponent, // ✅ AJOUT
  ]
})
export class AdminLayoutModule {}