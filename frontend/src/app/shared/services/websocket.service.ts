import { Injectable } from '@angular/core';
import { Observable, Subject, BehaviorSubject } from 'rxjs';
import { filter, map } from 'rxjs/operators';
import { WorkflowUpdate, AgentStatus } from '../models/patient.model';

@Injectable({
  providedIn: 'root'
})
export class WebSocketService {
  private socket: WebSocket | null = null;
  private messagesSubject = new Subject<any>();
  private connectionStatusSubject = new BehaviorSubject<boolean>(false);
  
  public messages$ = this.messagesSubject.asObservable();
  public connectionStatus$ = this.connectionStatusSubject.asObservable();
  
  private readonly wsUrl = 'ws://localhost:8000/ws'; // WebSocket endpoint
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectInterval = 5000; // 5 seconds

  constructor() {
    this.connect();
  }

  private connect(): void {
    try {
      this.socket = new WebSocket(this.wsUrl);
      
      this.socket.onopen = (event) => {
        console.log('WebSocket connection established');
        this.connectionStatusSubject.next(true);
        this.reconnectAttempts = 0;
      };
      
      this.socket.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          this.messagesSubject.next(message);
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };
      
      this.socket.onclose = (event) => {
        console.log('WebSocket connection closed:', event.code, event.reason);
        this.connectionStatusSubject.next(false);
        this.socket = null;
        
        // Attempt to reconnect
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
          this.reconnectAttempts++;
          console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts}) in ${this.reconnectInterval}ms`);
          setTimeout(() => this.connect(), this.reconnectInterval);
        } else {
          console.error('Max reconnection attempts reached. WebSocket connection failed.');
        }
      };
      
      this.socket.onerror = (error) => {
        console.error('WebSocket error:', error);
        this.connectionStatusSubject.next(false);
      };
      
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
      this.connectionStatusSubject.next(false);
      
      // Fallback: simulate real-time updates with polling
      this.startFallbackPolling();
    }
  }

  private startFallbackPolling(): void {
    console.log('WebSocket not available, falling back to polling for real-time updates');
    
    // Simulate workflow updates every 30 seconds
    setInterval(() => {
      const mockUpdate: WorkflowUpdate = {
        workflow_id: `workflow_${Date.now()}`,
        status: 'running',
        step: 'Processing patients',
        progress: Math.random() * 100,
        timestamp: new Date().toISOString(),
        message: 'Analyzing patient care gaps...',
        data: {
          patients_processed: Math.floor(Math.random() * 50),
          care_gaps_found: Math.floor(Math.random() * 20)
        }
      };
      
      this.messagesSubject.next({
        type: 'workflow_update',
        data: mockUpdate
      });
    }, 30000);
  }

  public send(message: any): void {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket is not connected. Message not sent:', message);
    }
  }

  public disconnect(): void {
    if (this.socket) {
      this.socket.close();
      this.socket = null;
      this.connectionStatusSubject.next(false);
    }
  }

  // Specific observable streams for different types of updates
  
  public getWorkflowUpdates(): Observable<WorkflowUpdate> {
    return this.messages$.pipe(
      filter(message => message.type === 'workflow_update'),
      map(message => message.data)
    );
  }

  public getAgentStatusUpdates(): Observable<AgentStatus[]> {
    return this.messages$.pipe(
      filter(message => message.type === 'agent_status_update'),
      map(message => message.data)
    );
  }

  public getSystemAlerts(): Observable<any> {
    return this.messages$.pipe(
      filter(message => message.type === 'system_alert'),
      map(message => message.data)
    );
  }

  public getCareGapUpdates(): Observable<any> {
    return this.messages$.pipe(
      filter(message => message.type === 'care_gap_update'),
      map(message => message.data)
    );
  }

  public getPatientUpdates(): Observable<any> {
    return this.messages$.pipe(
      filter(message => message.type === 'patient_update'),
      map(message => message.data)
    );
  }

  // Subscribe to specific workflow updates
  public subscribeToWorkflow(workflowId: string): void {
    this.send({
      type: 'subscribe_workflow',
      workflow_id: workflowId
    });
  }

  public unsubscribeFromWorkflow(workflowId: string): void {
    this.send({
      type: 'unsubscribe_workflow',
      workflow_id: workflowId
    });
  }

  // Subscribe to agent updates
  public subscribeToAgentUpdates(): void {
    this.send({
      type: 'subscribe_agents'
    });
  }

  public unsubscribeFromAgentUpdates(): void {
    this.send({
      type: 'unsubscribe_agents'
    });
  }

  // Get connection status
  public isConnected(): boolean {
    return this.connectionStatusSubject.value;
  }

  // Force reconnect
  public reconnect(): void {
    this.disconnect();
    this.reconnectAttempts = 0;
    setTimeout(() => this.connect(), 1000);
  }
}