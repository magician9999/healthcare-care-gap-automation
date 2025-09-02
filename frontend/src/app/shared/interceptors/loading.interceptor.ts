import { Injectable } from '@angular/core';
import { HttpInterceptor, HttpRequest, HttpHandler, HttpEvent } from '@angular/common/http';
import { Observable } from 'rxjs';
import { finalize } from 'rxjs/operators';
import { LoadingService } from '../services/loading.service';

@Injectable()
export class LoadingInterceptor implements HttpInterceptor {
  
  constructor(private loadingService: LoadingService) {}

  intercept(req: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
    // Skip loading indicator for certain requests
    if (req.url.includes('/health') || req.url.includes('/metrics')) {
      return next.handle(req);
    }

    // Start loading
    this.loadingService.setLoading(true);

    return next.handle(req).pipe(
      finalize(() => {
        // Stop loading when request completes (success or error)
        this.loadingService.setLoading(false);
      })
    );
  }
}