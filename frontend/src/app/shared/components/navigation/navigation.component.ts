import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';

interface NavigationItem {
  title: string;
  icon: string;
  route: string;
  badge?: number;
  description?: string;
}

@Component({
  selector: 'app-navigation',
  templateUrl: './navigation.component.html',
  styleUrls: ['./navigation.component.scss']
})
export class NavigationComponent implements OnInit {
  
  navigationItems: NavigationItem[] = [
    {
      title: 'Dashboard',
      icon: 'dashboard',
      route: '/dashboard',
      description: 'System overview and real-time status'
    },
    {
      title: 'Campaigns',
      icon: 'campaign',
      route: '/campaigns',
      description: 'Manage patient outreach campaigns'
    },
    {
      title: 'Patients',
      icon: 'people',
      route: '/patients',
      description: 'Patient list and care gaps'
    },
    {
      title: 'Workflows',
      icon: 'account_tree',
      route: '/workflows',
      description: 'Monitor agent workflows'
    },
    {
      title: 'Analytics',
      icon: 'analytics',
      route: '/analytics',
      description: 'Performance metrics and insights'
    }
  ];

  currentRoute: string = '';

  constructor(private router: Router) { }

  ngOnInit(): void {
    this.currentRoute = this.router.url;
    this.router.events.subscribe(() => {
      this.currentRoute = this.router.url;
    });
  }

  navigate(route: string): void {
    this.router.navigate([route]);
  }

  isActive(route: string): boolean {
    return this.currentRoute === route;
  }
}