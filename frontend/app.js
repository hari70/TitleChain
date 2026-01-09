/**
 * TitleChain Frontend Application
 * 
 * Handles the 3-step demo flow:
 * 1. Create Identity (DID)
 * 2. Upload & Analyze Deed
 * 3. Issue Verifiable Credential
 */

const API_BASE = window.location.origin;

// Application State
const state = {
    userId: null,
    userDid: null,
    analysisId: null,
    credentialId: null,
    rawCredential: null
};

// =============================================================================
// Step 1: Create Identity
// =============================================================================

async function createIdentity() {
    const userId = document.getElementById('userId').value.trim();
    const userName = document.getElementById('userName').value.trim();
    
    if (!userId) {
        showNotification('Please enter a user ID', 'error');
        return;
    }
    
    // Validate user ID format
    if (!/^[a-zA-Z0-9_-]+$/.test(userId)) {
        showNotification('User ID can only contain letters, numbers, underscores, and hyphens', 'error');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/identity/create`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: userId,
                name: userName || null
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to create identity');
        }
        
        const data = await response.json();
        
        // Update state
        state.userId = userId;
        state.userDid = data.did;
        
        // Update UI
        document.getElementById('userDid').textContent = data.did;
        document.getElementById('identityResult').classList.remove('hidden');
        
        // Enable step 2
        transitionToStep(2);
        
        showNotification('Identity created successfully!', 'success');
        console.log('Identity created:', data);
        
    } catch (error) {
        showNotification(`Error: ${error.message}`, 'error');
        console.error('Create identity error:', error);
    }
}

// =============================================================================
// Step 2: Upload Deed
// =============================================================================

async function uploadDeed() {
    const fileInput = document.getElementById('deedFile');
    const file = fileInput.files[0];
    
    if (!file) return;
    
    // Show progress
    document.getElementById('uploadProgress').classList.remove('hidden');
    document.getElementById('analysisResult').classList.add('hidden');
    
    try {
        const formData = new FormData();
        formData.append('file', file);
        
        // Add user_id as query parameter
        const url = state.userId 
            ? `${API_BASE}/title/upload?user_id=${encodeURIComponent(state.userId)}`
            : `${API_BASE}/title/upload`;
        
        const response = await fetch(url, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to analyze document');
        }
        
        const data = await response.json();
        
        // Update state
        state.analysisId = data.analysis_id;
        
        // Get full analysis
        const fullResponse = await fetch(`${API_BASE}/title/analyze/${data.analysis_id}`);
        const fullData = await fullResponse.json();
        
        // Update UI
        document.getElementById('uploadProgress').classList.add('hidden');
        document.getElementById('analysisResult').classList.remove('hidden');
        
        // Document type
        const docType = fullData.parsed_deed.document_type || 'unknown';
        document.getElementById('docType').textContent = 
            docType.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
        
        // Risk score with color
        const riskScore = fullData.risk_analysis.risk_score || 0;
        const riskLevel = fullData.risk_analysis.risk_level || 'UNKNOWN';
        const riskEl = document.getElementById('riskScore');
        riskEl.textContent = `${(riskScore * 100).toFixed(0)}% (${riskLevel})`;
        riskEl.className = `text-xl font-bold mt-1 ${
            riskLevel === 'LOW' ? 'text-green-600' : 
            riskLevel === 'MEDIUM' ? 'text-yellow-600' : 
            'text-red-600'
        }`;
        
        // Parties
        const grantor = fullData.parsed_deed.parties?.grantor?.names?.join(', ') || 'Unknown';
        const grantee = fullData.parsed_deed.parties?.grantee?.names?.join(', ') || 'Unknown';
        document.getElementById('parties').innerHTML = `
            <span class="text-gray-500">From:</span> ${grantor}<br>
            <span class="text-gray-500">To:</span> ${grantee}
        `;
        
        // Full analysis JSON
        document.getElementById('fullAnalysis').textContent = 
            JSON.stringify(fullData, null, 2);
        
        // Enable step 3
        transitionToStep(3);
        
        showNotification('Document analyzed successfully!', 'success');
        console.log('Analysis complete:', fullData);
        
    } catch (error) {
        document.getElementById('uploadProgress').classList.add('hidden');
        showNotification(`Error: ${error.message}`, 'error');
        console.error('Upload error:', error);
    }
}

// =============================================================================
// Step 3: Issue Credential
// =============================================================================

async function issueCredential() {
    if (!state.userId || !state.analysisId) {
        showNotification('Please complete previous steps first', 'error');
        return;
    }
    
    try {
        const response = await fetch(
            `${API_BASE}/credential/issue?user_id=${encodeURIComponent(state.userId)}&analysis_id=${encodeURIComponent(state.analysisId)}`,
            { method: 'POST' }
        );
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to issue credential');
        }
        
        const data = await response.json();
        state.credentialId = data.credential.id.split(':').pop();
        state.rawCredential = data.credential;
        
        // Update UI
        document.getElementById('credentialResult').classList.remove('hidden');
        
        const subject = data.credential.credentialSubject;
        document.getElementById('credSubject').textContent = 
            subject.propertyAddress || 
            (subject.legalDescription ? subject.legalDescription.substring(0, 60) + '...' : 'Property Credential');
        
        // Risk badge
        const riskLevel = subject.riskAssessment.level;
        const riskBadge = document.getElementById('riskBadge');
        riskBadge.textContent = riskLevel;
        riskBadge.className = `px-3 py-1 rounded-full text-sm font-bold ${
            riskLevel === 'LOW' ? 'bg-green-100 text-green-800' :
            riskLevel === 'MEDIUM' ? 'bg-yellow-100 text-yellow-800' :
            'bg-red-100 text-red-800'
        }`;
        
        // Dates
        document.getElementById('credIssued').textContent = 
            new Date(data.credential.issuanceDate).toLocaleDateString();
        document.getElementById('credExpires').textContent = 
            new Date(data.credential.expirationDate).toLocaleDateString();
        
        // Raw credential JSON
        document.getElementById('rawCredential').textContent = 
            JSON.stringify(data.credential, null, 2);
        
        // Mark step 3 complete
        document.getElementById('step3-indicator').classList.remove('step-active');
        document.getElementById('step3-indicator').classList.add('step-complete');
        
        showNotification('Credential issued successfully!', 'success');
        console.log('Credential issued:', data);
        
    } catch (error) {
        showNotification(`Error: ${error.message}`, 'error');
        console.error('Issue credential error:', error);
    }
}

// =============================================================================
// Credential Actions
// =============================================================================

async function verifyCredential() {
    if (!state.credentialId) {
        showNotification('No credential to verify', 'error');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/credential/verify/${state.credentialId}`);
        const data = await response.json();
        
        if (data.verification_result.valid) {
            const checks = Object.entries(data.verification_result.checks)
                .map(([k, v]) => `${v ? '✓' : '✗'} ${k.replace(/_/g, ' ')}`)
                .join('\n');
            
            showNotification(
                `✅ Credential Verified!\n\nAll checks passed:\n${checks}`, 
                'success',
                5000
            );
        } else {
            const errors = data.verification_result.errors.join('\n• ');
            showNotification(
                `❌ Verification Failed!\n\nIssues:\n• ${errors}`, 
                'error',
                5000
            );
        }
        
        console.log('Verification result:', data);
        
    } catch (error) {
        showNotification(`Verification error: ${error.message}`, 'error');
        console.error('Verify error:', error);
    }
}

function copyCredential() {
    if (!state.rawCredential) {
        showNotification('No credential to copy', 'error');
        return;
    }
    
    const json = JSON.stringify(state.rawCredential, null, 2);
    navigator.clipboard.writeText(json).then(() => {
        showNotification('Credential JSON copied to clipboard!', 'success');
    }).catch(err => {
        showNotification('Failed to copy: ' + err.message, 'error');
    });
}

// =============================================================================
// UI Helpers
// =============================================================================

function transitionToStep(step) {
    // Update indicators
    for (let i = 1; i <= 3; i++) {
        const indicator = document.getElementById(`step${i}-indicator`);
        const panel = document.getElementById(`step${i}`);
        
        if (i < step) {
            indicator.classList.remove('step-active');
            indicator.classList.add('step-complete');
        } else if (i === step) {
            indicator.classList.add('step-active');
            indicator.classList.remove('step-complete', 'border-gray-200');
            panel.classList.remove('opacity-50', 'pointer-events-none');
        }
    }
    
    // Scroll to new step
    document.getElementById(`step${step}`).scrollIntoView({ 
        behavior: 'smooth', 
        block: 'center' 
    });
}

function showNotification(message, type = 'info', duration = 3000) {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `fixed top-4 right-4 p-4 rounded-lg shadow-lg z-50 max-w-md transition-all transform translate-x-full ${
        type === 'success' ? 'bg-green-500 text-white' :
        type === 'error' ? 'bg-red-500 text-white' :
        'bg-blue-500 text-white'
    }`;
    notification.style.whiteSpace = 'pre-line';
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    // Animate in
    setTimeout(() => {
        notification.classList.remove('translate-x-full');
    }, 10);
    
    // Remove after duration
    setTimeout(() => {
        notification.classList.add('translate-x-full');
        setTimeout(() => notification.remove(), 300);
    }, duration);
}

// =============================================================================
// Initialize
// =============================================================================

document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 TitleChain Frontend loaded');
    console.log('📡 API Base:', API_BASE);
    
    // Check API availability
    fetch(`${API_BASE}/health`)
        .then(r => r.json())
        .then(data => {
            console.log('✅ API connected:', data);
        })
        .catch(err => {
            console.error('❌ API not available:', err);
            showNotification(
                'API not available. Make sure the backend is running on port 8000.', 
                'error',
                5000
            );
        });
    
    // Enable Enter key for user ID input
    document.getElementById('userId').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') createIdentity();
    });
});
