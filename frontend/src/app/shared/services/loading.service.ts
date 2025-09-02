import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class LoadingService {
  private loadingSubject = new BehaviorSubject<boolean>(false);
  private loadingCounter = 0;

  constructor() { }

  get loading$(): Observable<boolean> {
    return this.loadingSubject.asObservable();
  }

  get isLoading(): boolean {
    return this.loadingSubject.value;
  }

  setLoading(loading: boolean): void {
    if (loading) {
      this.loadingCounter++;
      this.loadingSubject.next(true);
    } else {
      this.loadingCounter--;
      if (this.loadingCounter <= 0) {
        this.loadingCounter = 0;
        this.loadingSubject.next(false);
      }
    }
  }

  forceStopLoading(): void {
    this.loadingCounter = 0;
    this.loadingSubject.next(false);
  }
}