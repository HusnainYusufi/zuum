// All Checkins Page JavaScript

let currentPage = 1;
let totalPages = 1;
let checkins = [];

// Initialize page
document.addEventListener('DOMContentLoaded', function() {
    loadCheckins(1);
    setupEventListeners();
});

function setupEventListeners() {
    // Filter event listeners
    document.getElementById('call-status-filter').addEventListener('change', applyFilters);
    document.getElementById('issue-filter').addEventListener('change', applyFilters);
    document.getElementById('review-filter').addEventListener('change', applyFilters);
    document.getElementById('time-filter').addEventListener('change', applyFilters);
    document.getElementById('tags-filter').addEventListener('input', debounce(applyFilters, 300));
    document.getElementById('name-filter').addEventListener('input', debounce(applyFilters, 300));
    document.getElementById('phone-filter').addEventListener('input', debounce(applyFilters, 300));
    document.getElementById('load-id-filter').addEventListener('input', debounce(applyFilters, 300));
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

async function loadCheckins(page = 1) {
    try {
        const filters = getFilters();
        const { sort_by_time, call_status, ...apiFilters } = filters;
        
        const queryParams = new URLSearchParams({
            page: page,
            per_page: 15,
            ...apiFilters
        });
        
        const response = await fetch(`/api/checkin/list?${queryParams}`);
        const data = await response.json();
        
        if (data.status === 'success') {
            checkins = data.data.checkins;
            
            // Apply client-side call status filtering
            if (call_status) {
                checkins = checkins.filter(checkin => {
                    if (call_status === 'answered') {
                        return checkin.user_picked_up === true || checkin.user_picked_up === 'true';
                    } else if (call_status === 'not_answered') {
                        return checkin.user_picked_up === false || checkin.user_picked_up === 'false';
                    }
                    return true;
                });
            }
            
            // Apply client-side time sorting
            const sortOrder = sort_by_time || 'desc';
            checkins.sort((a, b) => {
                const dateA = new Date(a.AI_Timestamp);
                const dateB = new Date(b.AI_Timestamp);
                return sortOrder === 'asc' ? dateA - dateB : dateB - dateA;
            });
            
            currentPage = data.data.current_page;
            totalPages = data.data.total_pages;
            
            displayCheckins(checkins);
            updatePagination();
        }
    } catch (error) {
        console.error('Error loading check-ins:', error);
        document.getElementById('checkins-content').innerHTML = '<p class="no-check-ins">Error loading check-ins</p>';
    }
}

function getFilters() {
    const filters = {};
    
    const callStatusFilter = document.getElementById('call-status-filter').value;
    if (callStatusFilter) filters.call_status = callStatusFilter;
    
    const issueFilter = document.getElementById('issue-filter').value;
    if (issueFilter) filters.issue_flagged = issueFilter;
    
    const reviewFilter = document.getElementById('review-filter').value;
    if (reviewFilter) filters.requires_review = reviewFilter;
    
    const timeFilter = document.getElementById('time-filter').value;
    if (timeFilter) filters.sort_by_time = timeFilter;
    
    const tagsFilter = document.getElementById('tags-filter').value.trim();
    if (tagsFilter) filters.tags = tagsFilter;
    
    const nameFilter = document.getElementById('name-filter').value.trim();
    if (nameFilter) filters.search_name = nameFilter;
    
    const phoneFilter = document.getElementById('phone-filter').value.trim();
    if (phoneFilter) filters.search_phone = phoneFilter;
    
    const loadIdFilter = document.getElementById('load-id-filter').value.trim();
    if (loadIdFilter) filters.search_load_id = loadIdFilter;
    
    return filters;
}

function applyFilters() {
    // Update filter visual state
    const filterElements = [
        'call-status-filter', 'issue-filter', 'review-filter', 'time-filter',
        'tags-filter', 'name-filter', 'phone-filter', 'load-id-filter'
    ];
    
    filterElements.forEach(id => {
        const element = document.getElementById(id);
        const hasValue = element.value && element.value.trim() !== '';
        element.classList.toggle('active', hasValue);
    });
    
    currentPage = 1;
    loadCheckins(1);
}

function displayCheckins(checkins) {
    const container = document.getElementById('checkins-content');
    
    if (!checkins || checkins.length === 0) {
        container.innerHTML = '<p class="no-check-ins">No check-ins found</p>';
        return;
    }
    
    const checkinsHtml = checkins.map(checkin => {
        const date = new Date(checkin.AI_Timestamp);
        const dateStr = date.toLocaleDateString('en-US', { 
            month: 'short', 
            day: 'numeric', 
            year: 'numeric' 
        });
        const timeStr = date.toLocaleTimeString('en-US', { 
            hour: 'numeric', 
            minute: '2-digit',
            hour12: true 
        });
        
        // Extract name, phone, and country code from checkin.Forms JSON
        let name = '';
        let phone = '';
        let countryCode = '';
        let loadId = '';
        let formType = '';
        let formsData = checkin.forms || checkin.Forms;
        if (formsData) {
            try {
                const forms = typeof formsData === 'string' ? JSON.parse(formsData) : formsData;
                if ('pickup_load_id' in forms) {
                    name = forms['pickup_trucker_name'] || '';
                    phone = forms['pickup_contact_phone'] || '';
                    countryCode = forms['pickup_country_code'] || '';
                    loadId = forms['pickup_load_id'] || '';
                    formType = 'At Pickup';
                } else if ('pc_load_id' in forms) {
                    name = forms['pc_trucker_name'] || '';
                    phone = forms['pc_contact_phone'] || '';
                    countryCode = forms['pc_country_code'] || '';
                    loadId = forms['pc_load_id'] || '';
                    formType = 'Pickup Complete';
                } else if ('it_load_id' in forms) {
                    name = forms['it_trucker_name'] || '';
                    phone = forms['it_contact_phone'] || '';
                    countryCode = forms['it_country_code'] || '';
                    loadId = forms['it_load_id'] || '';
                    formType = 'In Transit';
                } else if ('ad_load_id' in forms) {
                    name = forms['ad_trucker_name'] || '';
                    phone = forms['ad_contact_phone'] || '';
                    countryCode = forms['ad_country_code'] || '';
                    loadId = forms['ad_load_id'] || '';
                    formType = 'At Drop';
                } else if ('del_load_id' in forms) {
                    name = forms['del_trucker_name'] || '';
                    phone = forms['del_contact_phone'] || '';
                    countryCode = forms['del_country_code'] || '';
                    loadId = forms['del_load_id'] || '';
                    formType = 'Delivered';
                } else if ('pod_load_id' in forms) {
                    name = forms['pod_trucker_name'] || '';
                    phone = forms['pod_contact_phone'] || '';
                    countryCode = forms['pod_country_code'] || '';
                    loadId = forms['pod_load_id'] || '';
                    formType = 'Request POD';
                }
            } catch (err) {
                console.log('Error parsing checkin.forms:', err, formsData);
            }
        }
        
        // Process tags for display
        let tags = 'No tags';
        if (checkin.Tags) {
            try {
                if (checkin.Tags.startsWith('[') && checkin.Tags.endsWith(']')) {
                    const tagsArray = JSON.parse(checkin.Tags);
                    tags = Array.isArray(tagsArray) ? tagsArray.join(', ') : 'No tags';
                } else {
                    tags = checkin.Tags.split(',').map(tag => tag.trim()).filter(tag => tag).join(', ');
                }
            } catch (error) {
                tags = checkin.Tags.split(',').map(tag => tag.trim()).filter(tag => tag).join(', ');
            }
        }
        
        // Extract call direction from tags for symbol
        let callDirectionSymbol = '';
        let tagsArray = [];
        
        if (checkin.Tags) {
            try {
                if (checkin.Tags.startsWith('[') && checkin.Tags.endsWith(']')) {
                    tagsArray = JSON.parse(checkin.Tags);
                } else {
                    tagsArray = checkin.Tags.split(',').map(tag => tag.trim()).filter(tag => tag);
                }
            } catch (error) {
                tagsArray = checkin.Tags.split(',').map(tag => tag.trim()).filter(tag => tag);
            }
        }
        
        if (Array.isArray(tagsArray) && tagsArray.length > 1) {
            const callDirection = tagsArray[1];
            if (callDirection === 'inbound') {
                callDirectionSymbol = '<i class="fas fa-phone status-icon" style="color: #28a745;" title="Inbound call"></i><i class="fas fa-long-arrow-alt-down" style="color: #28a745; font-size: 0.6em; margin-left: 2px;"></i>';
            } else if (callDirection === 'outbound') {
                callDirectionSymbol = '<i class="fas fa-phone status-icon" style="color: #007bff;" title="Outbound call"></i><i class="fas fa-long-arrow-alt-up" style="color: #007bff; font-size: 0.6em; margin-left: 2px;"></i>';
            }
        }
        
        return `
            <div class="modal-check-in-card" onclick="window.location.href='/checkin/${checkin.id}'">
                <div class="modal-check-in-header" style="padding: 8px 12px; margin-bottom: 6px;">
                    <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                        <span class="modal-check-in-id" style="font-size: 14px;">#${checkin.id}</span>
                        ${checkin.call_status === 'in_progress' && !checkin.AI_Response_Summary ? `
                        <div class="modal-active-indicator" style="padding: 2px 6px; font-size: 11px;">
                            <div class="modal-active-spinner" style="width: 10px; height: 10px;"></div>
                            <span>Call Active</span>
                        </div>
                        ` : ''}
                        <span class="modal-check-in-timestamp" style="font-size: 12px; padding: 2px 6px;">
                            <i class="fas fa-clock"></i>
                            ${dateStr} at ${timeStr}
                        </span>
                        <span class="modal-check-in-formtype" style="display: flex; align-items: center; gap: 3px; font-size: 12px; padding: 2px 6px;">
                            <i class="fas fa-clipboard-list"></i>
                            ${formType || checkin.form_type_name || checkin.form_type || 'Default Form'}
                        </span>
                        <span class="modal-check-in-loadid" style="display: flex; align-items: center; gap: 3px; font-size: 12px; padding: 2px 6px;">
                            <i class="fas fa-truck"></i>
                            ${checkin.load_id || 'N/A'}
                        </span>
                    </div>
                    <div class="modal-check-in-status" style="display: flex; align-items: center; gap: 6px;">
                        <span class="modal-check-in-tags" style="color: #888; font-size: 11px;">
                            <i class="fas fa-tags" style="font-size: 0.9em; margin-right: 2px;"></i>
                            ${tags}
                        </span>
                        ${callDirectionSymbol}
                        ${(checkin.user_picked_up === false || checkin.user_picked_up === 'false' || checkin.user_picked_up === 'False') ? 
                            '<i class="fas fa-phone-slash status-icon error" style="font-size: 16px;" title="User did not pick up phone"></i>' : 
                            checkin.Issue_Flagged ? 
                                '<i class="fas fa-exclamation-triangle status-icon warning" style="font-size: 16px;"></i>' : 
                                '<i class="fas fa-check-circle status-icon success" style="font-size: 16px;"></i>'}
                        ${checkin.call_trasfered || checkin.call_status === 'transferred' ? 
                            '<i class="fas fa-phone-alt status-icon transfer" style="font-size: 16px;"></i>' : ''}
                    </div>
                </div>
                <div class="modal-check-in-content" style="padding: 0 12px 8px 12px;">
                    <div class="modal-check-in-field" style="margin-bottom: 4px; font-size: 13px;">
                        <span class="modal-field-label" style="font-size: 11px;">Name:</span>
                        <span class="modal-field-value" style="font-size: 13px;">${name || checkin.trucker_name || checkin.Trucker_Name || 'N/A'}</span>
                        <span class="modal-field-label" style="margin-left: 12px; font-size: 11px;">Phone:</span>
                        <span class="modal-field-value" style="font-size: 13px;">
                            ${countryCode ? `${countryCode} ` : ''}
                            ${phone || checkin.contact_phone || checkin.Contact_Phone || 'N/A'}
                        </span>
                    </div>
                    ${checkin.AI_Response_Summary ? `
                    <div class="modal-summary-field" style="padding: 6px 8px; margin-top: 4px;">
                        <div class="modal-field-label" style="font-size: 11px; margin-bottom: 3px;">AI Summary</div>
                        <div class="modal-field-value" style="font-size: 12px; line-height: 1.3;">${checkin.AI_Response_Summary}</div>
                    </div>
                    ` : ''}
                </div>
            </div>
        `;
    }).join('');
    
    container.innerHTML = checkinsHtml;
}

function updatePagination() {
    const container = document.getElementById('pagination');
    
    if (totalPages <= 1) {
        container.innerHTML = '';
        return;
    }
    
    let paginationHtml = '<div class="pagination">';
    
    // Previous button
    paginationHtml += `<button ${currentPage === 1 ? 'disabled' : ''} onclick="changePage(${currentPage - 1})">
        <i class="fas fa-chevron-left"></i> Previous
    </button>`;
    
    // Page numbers
    const startPage = Math.max(1, currentPage - 2);
    const endPage = Math.min(totalPages, currentPage + 2);
    
    if (startPage > 1) {
        paginationHtml += `<button onclick="changePage(1)">1</button>`;
        if (startPage > 2) {
            paginationHtml += `<span style="color: #718096;">...</span>`;
        }
    }
    
    for (let i = startPage; i <= endPage; i++) {
        paginationHtml += `<button class="${i === currentPage ? 'active' : ''}" onclick="changePage(${i})">${i}</button>`;
    }
    
    if (endPage < totalPages) {
        if (endPage < totalPages - 1) {
            paginationHtml += `<span style="color: #718096;">...</span>`;
        }
        paginationHtml += `<button onclick="changePage(${totalPages})">${totalPages}</button>`;
    }
    
    // Next button
    paginationHtml += `<button ${currentPage === totalPages ? 'disabled' : ''} onclick="changePage(${currentPage + 1})">
        Next <i class="fas fa-chevron-right"></i>
    </button>`;
    
    paginationHtml += '</div>';
    container.innerHTML = paginationHtml;
}

function changePage(page) {
    if (page >= 1 && page <= totalPages && page !== currentPage) {
        loadCheckins(page);
    }
} 