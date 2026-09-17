// API Configuration
const API_BASE_URL = "http://127.0.0.1:8000";

// Utility functions
function showError(message) {
    const errorElement = document.getElementById('error-message');
    errorElement.textContent = message;
    errorElement.style.display = 'block';
    setTimeout(() => {
        errorElement.style.display = 'none';
        errorElement.textContent = '';
    }, 5000);
}

function updateHealthStatus(isHealthy) {
    const indicator = document.getElementById('health-indicator');
    const text = document.getElementById('health-status-text');
    
    if (isHealthy) {
        indicator.style.backgroundColor = '#4caf50';
        text.textContent = 'Healthy';
    } else {
        indicator.style.backgroundColor = '#ff5252';
        text.textContent = 'Unhealthy';
    }
}

function formatTimestamp(timestamp) {
    if (!timestamp) return 'N/A';
    return new Date(timestamp).toLocaleString();
}

function renderTraceEntry(entry) {
    const entryEl = document.createElement('div');
    entryEl.className = 'trace-entry';
    
    const timestampEl = document.createElement('div');
    timestampEl.className = 'timestamp';
    timestampEl.textContent = formatTimestamp(entry.timestamp);
    
    const eventTypeEl = document.createElement('div');
    eventTypeEl.className = 'event-type';
    eventTypeEl.textContent = entry.event_type || 'event';
    
    const agentEl = document.createElement('div');
    agentEl.className = 'agent';
    agentEl.textContent = entry.agent || 'Unknown';
    
    const toolEl = document.createElement('div');
    toolEl.className = 'tool';
    toolEl.textContent = entry.tool || 'No tool';
    
    const messageEl = document.createElement('div');
    messageEl.className = 'message';
    messageEl.textContent = entry.message || '';
    
    let dataHtml = '';
    if (entry.data) {
        const dataEl = document.createElement('div');
        dataEl.className = 'data';
        dataEl.textContent = JSON.stringify(entry.data);
        entryEl.appendChild(dataEl);
    }
    
    entryEl.appendChild(timestampEl);
    entryEl.appendChild(eventTypeEl);
    entryEl.appendChild(agentEl);
    entryEl.appendChild(toolEl);
    entryEl.appendChild(messageEl);
    
    return entryEl;
}

// App initialization
document.addEventListener('DOMContentLoaded', () => {
    const workflowForm = document.getElementById('workflow-form');
    const runWorkflowBtn = document.getElementById('run-workflow-btn');
    const loadingState = document.getElementById('loading-state');
    const workflowInfo = document.getElementById('workflow-info');
    const tracePanel = document.getElementById('trace-panel');
    const resultsPanel = document.getElementById('results-panel');
    
    // Check backend health
    fetch(`${API_BASE_URL}/health`)
        .then(response => {
            if (response.ok) {
                return response.json();
            } else {
                throw new Error('Backend unhealthy');
            }
        })
        .then(data => updateHealthStatus(true))
        .catch(error => {
            updateHealthStatus(false);
            showError('Cannot connect to backend. Please ensure the server is running at ' + API_BASE_URL);
        });
    
    // Workflow submission
    workflowForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const requestText = document.getElementById('workflow-request').value;
        const workflowName = document.getElementById('workflow-name').value;
        
        if (!requestText.trim()) {
            showError('Please enter a workflow request');
            return;
        }
        
        // Hide previous results and errors
        document.getElementById('error-message').style.display = 'none';
        document.getElementById('error-message').textContent = '';
        workflowInfo.style.display = 'none';
        tracePanel.style.display = 'none';
        resultsPanel.style.display = 'none';
        
        // Show loading state
        runWorkflowBtn.disabled = true;
        loadingState.style.display = 'block';
        
        try {
            const response = await fetch(`${API_BASE_URL}/workflows`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    request: requestText,
                    name: workflowName
                })
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
            }
            
            const workflowData = await response.json();
            
            // Update workflow info display
            document.getElementById('workflow-id').textContent = workflowData.id;
            document.getElementById('workflow-status').textContent = workflowData.status;
            document.getElementById('current-step').textContent = workflowData.current_step || 0;
            document.getElementById('current-agent').textContent = workflowData.current_agent || 'None';
            document.getElementById('created-time').textContent = formatTimestamp(workflowData.created_at);
            
            if (workflowData.completed_at) {
                document.getElementById('completed-time').textContent = formatTimestamp(workflowData.completed_at);
            } else {
                document.getElementById('completed-time').textContent = 'Not completed';
            }
            
            workflowInfo.style.display = 'grid';
            
            // Update agent visualization
            updateAgentStatus(workflowData.status, workflowData.current_agent);
            updateApprovalControls(workflowData);
            
            // Fetch trace for completed workflows
            if (workflowData.status === 'completed' || workflowData.status === 'failed' || workflowData.status === 'rejected') {
                fetchWorkflowTrace(workflowData.id);
            }
            
            // Poll for status updates if still running
            if (workflowData.status !== 'completed' && workflowData.status !== 'failed' && workflowData.status !== 'rejected') {
                pollWorkflowStatus(workflowData.id);
            }
            
        } catch (error) {
            showError(`Error creating workflow: ${error.message}`);
        } finally {
            runWorkflowBtn.disabled = false;
            loadingState.style.display = 'none';
        }
    });
    
    // Poll for workflow status updates
    function pollWorkflowStatus(workflowId) {
        const pollInterval = setInterval(async () => {
            try {
                const response = await fetch(`${API_BASE_URL}/workflows/${workflowId}`);
                
                if (!response.ok) {
                    if (response.status === 404) {
                        clearInterval(pollInterval);
                        return;
                    }
                    throw new Error(`Failed to fetch workflow status: ${response.status}`);
                }
                
                const workflowData = await response.json();
                
                // Update workflow info
                document.getElementById('workflow-status').textContent = workflowData.status;
                document.getElementById('current-step').textContent = workflowData.current_step || 0;
                document.getElementById('current-agent').textContent = workflowData.current_agent || 'None';
                
                // Update agent visualization
                updateAgentStatus(workflowData.status, workflowData.current_agent);
                updateApprovalControls(workflowData);
                
                // Check for completion
                if (workflowData.status === 'completed' || workflowData.status === 'failed' || workflowData.status === 'rejected') {
                    clearInterval(pollInterval);
                    
                    // For completed workflows, fetch trace (which contains execution details)
                    fetchWorkflowTrace(workflowId);
                }
                
            } catch (error) {
                console.error('Error polling workflow status:', error);
                clearInterval(pollInterval);
            }
        }, 2000); // Poll every 2 seconds
    }
    
    // Update agent status visualization
    function updateAgentStatus(status, currentAgent, traceEntries = []) {
    const agents = {
        planner: document.getElementById('planner-status'),
        research: document.getElementById('research-status'),
        database: document.getElementById('database-status'),
        code: document.getElementById('code-status'),
        synthesis: document.getElementById('synthesis-status')
    };

    // Reset all agents
    Object.entries(agents).forEach(([agent, element]) => {
        element.textContent = 'Not Run';
        element.className = `agent-status ${agent}`;
    });

    // Determine which agents actually executed
    const executedAgents = new Set();

    traceEntries.forEach(entry => {
        if (entry.agent && agents[entry.agent]) {
            executedAgents.add(entry.agent);
        }
    });

    // Mark agents that actually ran as completed
    executedAgents.forEach(agent => {
        agents[agent].textContent = 'Completed';
        agents[agent].className = `agent-status ${agent}`;
    });

    // During active execution, mark current agent as running
    if (status === 'running' || status === 'planning') {
        if (currentAgent && agents[currentAgent]) {
            agents[currentAgent].textContent = 'Running';
            agents[currentAgent].className = 'agent-status';
        }

        // Planner is active during planning even if trace hasn't arrived yet
        if (status === 'planning') {
            agents.planner.textContent = 'Running';
            agents.planner.className = 'agent-status';
        }
    }

    // Pending workflow
    if (status === 'pending') {
        agents.planner.textContent = 'Pending';
        agents.planner.className = 'agent-status';
    }

    // Failed workflow
    if (status === 'failed' && currentAgent && agents[currentAgent]) {
        agents[currentAgent].textContent = 'Failed';
        agents[currentAgent].className = 'agent-status';
    }

    // Rejected workflow
    if (status === 'rejected' && currentAgent && agents[currentAgent]) {
        agents[currentAgent].textContent = 'Rejected';
        agents[currentAgent].className = 'agent-status';
    }
}
    
    // Fetch and display workflow trace
    function fetchWorkflowTrace(workflowId) {
        fetch(`${API_BASE_URL}/workflows/${workflowId}/trace`)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`Failed to fetch trace: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                renderTrace(data);

                // Update agent visualization using actual execution trace
                const traceEntries = data.entries || [];
                const currentStatus = document.getElementById('workflow-status').textContent;
                const currentAgent = document.getElementById('current-agent').textContent;

                updateAgentStatus(
                    currentStatus,
                    currentAgent,
                    traceEntries
                );

                tracePanel.style.display = 'block';
            })
            .catch(error => {
                console.error('Error fetching trace:', error);
            });
    }
    
    // Render trace and display results
    function renderTrace(data) {
        const traceBody = document.getElementById('trace-body');
        traceBody.innerHTML = '';

        data.entries.forEach(entry => {
            const entryEl = renderTraceEntry(entry);
            traceBody.appendChild(entryEl);
        });

        // Scroll to bottom
        traceBody.scrollTop = traceBody.scrollHeight;
        
        // Display results from trace data
        displayResultsFromTrace(data);
    }
    
    // Display results from trace data
    function displayResultsFromTrace(data) {
        resultsPanel.style.display = 'block';
        
        const traceEntries = data.entries || [];
        
        // Find synthesis-related entries
        let synthesisData = null;
        let completionData = null;
        
        for (const entry of traceEntries) {
            if (entry.agent === 'synthesis' || entry.event_type === 'workflow_completed') {
                if (entry.data && typeof entry.data === 'object') {
                    if (entry.data.synthesized_response) {
                        synthesisData = entry.data.synthesized_response;
                    }
                    completionData = entry.data;
                }
            }
        }
        
        const resultContent = document.getElementById('result-content');
        
        if (synthesisData) {
            resultContent.textContent = synthesisData;
        } else if (completionData && completionData.status === 'completed') {
            resultContent.textContent = `Workflow completed successfully.\nStatus: ${completionData.status}\nSteps executed: ${completionData.current_step}\nFinal agent: ${completionData.current_agent}`;
        } else if (traceEntries.length > 0) {
            // Show summary of trace
            const summary = traceEntries.map(e => `${formatTimestamp(e.timestamp)} - ${e.agent}: ${e.message}`).join('\n');
            resultContent.textContent = `Workflow execution trace:\n\n${summary}`;
        } else {
            resultContent.textContent = 'Workflow executed. See trace panel for details.';
        }
        
        resultContent.style.display = 'block';
    }
    
    // Copy result to clipboard
    document.getElementById('copy-result-btn').addEventListener('click', () => {
        const resultContent = document.getElementById('result-content');
        if (resultContent.textContent && resultContent.textContent !== 'No results available') {
            navigator.clipboard.writeText(resultContent.textContent).then(() => {
                const btn = document.getElementById('copy-result-btn');
                const originalText = btn.textContent;
                btn.textContent = 'Copied!';
                setTimeout(() => {
                    btn.textContent = originalText;
                }, 2000);
            }).catch(err => {
                console.error('Failed to copy: ', err);
            });
        }
    });
    
    // Poll for workflow status updates and show/hide approval controls
    function updateApprovalControls(workflowData) {
        const approvalControls = document.getElementById('approval-controls');
        
        if (workflowData.status === 'paused_approval') {
            approvalControls.style.display = 'flex';
            approvalControls.style.gap = '1rem';
            approvalControls.style.marginTop = '1rem';
        } else {
            approvalControls.style.display = 'none';
        }
    }
    
    // Set up approval controls event listeners
    document.getElementById('approve-btn')?.addEventListener('click', async () => {
        const workflowId = document.getElementById('workflow-id').textContent;
        
        try {
            const response = await fetch(`${API_BASE_URL}/workflows/${workflowId}/approve`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (!response.ok) {
                throw new Error(`Failed to approve workflow: ${response.status}`);
            }
            
            const data = await response.json();
            
            document.getElementById('workflow-status').textContent = data.status;
            document.getElementById('current-agent').textContent = data.current_agent || 'None';
            
            updateAgentStatus(data.status, data.current_agent);
            updateApprovalControls(data);
            
        } catch (error) {
            showError(`Error approving workflow: ${error.message}`);
        }
    });
    
    document.getElementById('reject-btn')?.addEventListener('click', async () => {
        const workflowId = document.getElementById('workflow-id').textContent;
        
        try {
            const response = await fetch(`${API_BASE_URL}/workflows/${workflowId}/reject`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (!response.ok) {
                throw new Error(`Failed to reject workflow: ${response.status}`);
            }
            
            const data = await response.json();
            
            document.getElementById('workflow-status').textContent = data.status;
            document.getElementById('current-agent').textContent = data.current_agent || 'None';
            
            updateAgentStatus(data.status, data.current_agent);
            updateApprovalControls(data);
            
        } catch (error) {
            showError(`Error rejecting workflow: ${error.message}`);
        }
    });
});