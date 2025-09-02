import { Injectable } from '@angular/core';
import { HttpInterceptor, HttpRequest, HttpHandler, HttpEvent, HttpErrorResponse } from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { catchError, retry } from 'rxjs/operators';
import { MatSnackBar } from '@angular/material/snack-bar';

@Injectable()
export class ErrorInterceptor implements HttpInterceptor {
  
  constructor(private snackBar: MatSnackBar) {}

  intercept(req: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
    return next.handle(req).pipe(
      retry(1), // Retry failed requests once
      catchError((error: HttpErrorResponse) => {
        let errorMessage = 'An unexpected error occurred';
        
        if (error.error instanceof ErrorEvent) {
          // Client-side error
          errorMessage = error.error.message;
        } else {
          // Server-side error
          switch (error.status) {
            case 400:
              errorMessage = error.error?.detail || 'Bad Request';
              break;
            case 401:
              errorMessage = 'Unauthorized - Please check your credentials';
              break;
            case 403:
              errorMessage = 'Forbidden - You do not have permission to access this resource';
              break;
            case 404:
              errorMessage = error.error?.detail || 'Resource not found';
              break;
            case 422:
              if (error.error?.detail && Array.isArray(error.error.detail)) {
                errorMessage = error.error.detail.map((err: any) => err.msg).join(', ');
              } else {
                errorMessage = error.error?.detail || 'Validation error';
              }
              break;
            case 500:
              errorMessage = error.error?.detail || 'Internal server error';
              break;
            case 503:
              errorMessage = 'Service temporarily unavailable';
              break;
            default:
              errorMessage = error.error?.detail || `Error ${error.status}: ${error.statusText}`;
          }
        }

        // Show error notification
        this.showErrorNotification(errorMessage, error.status);

        // Log error for debugging
        console.error('HTTP Error:', {
          status: error.status,
          statusText: error.statusText,
          url: error.url,
          message: errorMessage,
          error: error.error
        });

        return throwError(() => ({
          message: errorMessage,
          status: error.status,
          statusText: error.statusText,
          url: error.url,
          originalError: error
        }));
      })
    );
  }

  private showErrorNotification(message: string, status?: number): void {
    const config = {
      duration: status && status >= 500 ? 8000 : 5000, // Longer duration for server errors
      verticalPosition: 'top' as const,
      horizontalPosition: 'center' as const,
      panelClass: ['error-snackbar']
    };

    this.snackBar.open(message, 'Dismiss', config);
  }
}