import { Routes } from '@angular/router';

//import { DashboardComponent } from '../../dashboard/dashboard.component';
//import { UserProfileComponent } from '../../user-profile/user-profile.component';
//import { TableListComponent } from '../../table-list/table-list.component';
//import { TypographyComponent } from '../../typography/typography.component';
//import { IconsComponent } from '../../icons/icons.component';
//import { MapsComponent } from '../../maps/maps.component';
//import { NotificationsComponent } from '../../notifications/notifications.component';
//import { UpgradeComponent } from '../../upgrade/upgrade.component';
import { AnalyzeComponent } from '../../analyze/analyze.component';
import { SimulationComponent } from '../../simulation/simulation.component'; // adapte le chemin si nécessaire
import { AnalyzeResultComponent } from '../../analyze-result/analyze-result.component';
import { HistoriqueComponent } from '../../historique/historique.component';
import { HomeComponent } from '../../home/home.component';
export const AdminLayoutRoutes: Routes = [
   
    

    //{ path: 'dashboard',      component: DashboardComponent },
    { path: 'analyze', component: AnalyzeComponent },
    
   
    //{ path: 'icons',          component: IconsComponent },
    
    { path: 'simulation', component: SimulationComponent },
    { path: 'analyze-result', component: AnalyzeResultComponent },
    { path: 'home', component: HomeComponent },
    { path: 'historique', component: HistoriqueComponent }
];
