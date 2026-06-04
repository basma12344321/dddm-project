import { NgModule } from '@angular/core';
import { RouterModule } from '@angular/router';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { AdminLayoutRoutes } from './admin-layout.routing';
//import { DashboardComponent } from '../../dashboard/dashboard.component';
//import { UserProfileComponent } from '../../user-profile/user-profile.component';
//import { TableListComponent } from '../../table-list/table-list.component';
//import { TypographyComponent } from '../../typography/typography.component';
//import { IconsComponent } from '../../icons/icons.component';
//import { MapsComponent } from '../../maps/maps.component';
//import { NotificationsComponent } from '../../notifications/notifications.component';
//import { UpgradeComponent } from '../../upgrade/upgrade.component';
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
//import { HomeComponent } from '../../home/home.component';
import { MatDividerModule } from '@angular/material/divider';

import { NgApexchartsModule } from "ng-apexcharts";


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
    //DashboardComponent,
    //UserProfileComponent,
    //TableListComponent,
    //TypographyComponent,
    //IconsComponent,
    //MapsComponent,
    //NotificationsComponent,
    //UpgradeComponent,
    AnalyzeComponent,
    AnalyzeResultComponent,
    SimulationComponent,
    //HomeComponent,
 
    
    
  ]
})

export class AdminLayoutModule {}
