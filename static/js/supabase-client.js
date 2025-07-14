/**
 * Supabase Client for Frontend RPC Calls
 * This file provides JavaScript functions to call Supabase RPC functions directly from templates
 */

class SupabaseClient {
    constructor(url, anonKey) {
        this.url = url;
        this.anonKey = anonKey;
        this.client = window.supabase?.createClient(url, anonKey);
    }

    async init() {
        // Check if Supabase JavaScript client is loaded
        if (!window.supabase) {
            console.error('Supabase JavaScript client not loaded. Please include the Supabase CDN script.');
            return false;
        }
        this.client = window.supabase.createClient(this.url, this.anonKey);
        return true;
    }

    // Dashboard Statistics
    async getDashboardStats() {
        try {
            const { data, error } = await this.client.rpc('get_dashboard_stats');
            if (error) throw error;
            return { success: true, data: data[0] || {} };
        } catch (error) {
            console.error('Error getting dashboard stats:', error);
            return { success: false, error: error.message };
        }
    }

    // Paginated Check-ins
    async getCheckInsPaginated(page = 1, pageSize = 10, filters = {}) {
        try {
            const { data, error } = await this.client.rpc('get_check_ins_paginated_enhanced', {
                page_num: page,
                page_size: pageSize,
                filter_issue_flagged: filters.issue_flagged || null,
                filter_tags: filters.tags || null,
                filter_call_status: filters.call_status || null,
                search_name: filters.search_name || null,
                search_phone: filters.search_phone || null,
                search_load_id: filters.search_load_id || null,
                start_date: filters.start_date || null,
                end_date: filters.end_date || null
            });
            
            if (error) throw error;
            
            // Process the data to separate checkins from total count
            const checkins = data || [];
            const totalCount = checkins.length > 0 ? checkins[0].total_count : 0;
            console.log("checkins", checkins);
            const totalPages = Math.ceil(totalCount / pageSize);
            
            return {
                success: true,
                data: {
                    checkins: checkins,
                    current_page: page,
                    per_page: pageSize,
                    total_count: totalCount,
                    total_pages: totalPages,
                    has_next: page < totalPages,
                    has_prev: page > 1
                }
            };
        } catch (error) {
            console.error('Error getting check-ins:', error);
            return { success: false, error: error.message };
        }
    }

    // Recent Check-ins with Call Info
    async getRecentCheckinsWithCalls(limit = 10) {
        try {
            const { data, error } = await this.client.rpc('get_recent_checkins_with_calls', {
                limit_count: limit
            });
            
            if (error) throw error;
            return { success: true, data: data || [] };
        } catch (error) {
            console.error('Error getting recent check-ins:', error);
            return { success: false, error: error.message };
        }
    }

    // Paginated Notifications
    async getNotificationsPaginated(page = 1, pageSize = 20, filters = {}) {
        try {
            const { data, error } = await this.client.rpc('get_notifications_paginated', {
                page_num: page,
                page_size: pageSize,
                filter_read: filters.read || null,
                filter_severity: filters.severity || null
            });
            
            if (error) throw error;
            
            const notifications = data || [];
            const totalCount = notifications.length > 0 ? notifications[0].total_count : 0;
            const totalPages = Math.ceil(totalCount / pageSize);
            
            return {
                success: true,
                data: {
                    notifications: notifications,
                    current_page: page,
                    per_page: pageSize,
                    total_count: totalCount,
                    total_pages: totalPages,
                    has_next: page < totalPages,
                    has_prev: page > 1
                }
            };
        } catch (error) {
            console.error('Error getting notifications:', error);
            return { success: false, error: error.message };
        }
    }

    // Mark Notification as Read
    async markNotificationRead(notificationId) {
        try {
            const { data, error } = await this.client.rpc('mark_notification_read', {
                notification_id: notificationId
            });
            
            if (error) throw error;
            return { success: true, marked_read: data };
        } catch (error) {
            console.error('Error marking notification as read:', error);
            return { success: false, error: error.message };
        }
    }

    // Direct table operations for when RPC isn't needed
    async getCheckIn(checkInId) {
        try {
            const { data, error } = await this.client
                .from('check_ins')
                .select('*, retell_calls(*)')
                .eq('id', checkInId)
                .single();
            
            if (error) throw error;
            return { success: true, data: data };
        } catch (error) {
            console.error('Error getting check-in:', error);
            return { success: false, error: error.message };
        }
    }

    // Update Check-in
    async updateCheckIn(checkInId, updates) {
        try {
            const { data, error } = await this.client
                .from('check_ins')
                .update(updates)
                .eq('id', checkInId)
                .select()
                .single();
            
            if (error) throw error;
            return { success: true, data: data };
        } catch (error) {
            console.error('Error updating check-in:', error);
            return { success: false, error: error.message };
        }
    }

    // Create Notification
    async createNotification(notification) {
        try {
            const { data, error } = await this.client
                .from('notifications')
                .insert(notification)
                .select()
                .single();
            
            if (error) throw error;
            return { success: true, data: data };
        } catch (error) {
            console.error('Error creating notification:', error);
            return { success: false, error: error.message };
        }
    }

    // Real-time subscriptions
    subscribeToCheckIns(callback) {
        return this.client
            .channel('check_ins_changes')
            .on('postgres_changes', 
                { event: '*', schema: 'public', table: 'check_ins' },
                callback
            )
            .subscribe();
    }

    subscribeToNotifications(callback) {
        return this.client
            .channel('notifications_changes')
            .on('postgres_changes', 
                { event: '*', schema: 'public', table: 'notifications' },
                callback
            )
            .subscribe();
    }

    // Unsubscribe from real-time updates
    unsubscribe(subscription) {
        if (subscription) {
            subscription.unsubscribe();
        }
    }
}

// Utility functions for frontend templates
window.SupabaseUtils = {
    // Format timestamp for display
    formatTimestamp(timestamp) {
        if (!timestamp) return '';
        const date = new Date(timestamp);
        return date.toLocaleString();
    },

    // Format tags array for display
    formatTags(tags) {
        if (!tags || !Array.isArray(tags)) return '';
        return tags.join(', ');
    },

    // Get severity badge class for notifications
    getSeverityClass(severity) {
        const classes = {
            'info': 'badge-info',
            'warning': 'badge-warning',
            'error': 'badge-danger',
            'success': 'badge-success'
        };
        return classes[severity] || 'badge-secondary';
    },

    // Format call status for display
    formatCallStatus(status) {
        const formats = {
            'in_progress': 'In Progress',
            'completed': 'Completed',
            'transferred': 'Transferred',
            'failed': 'Failed'
        };
        return formats[status] || status;
    },

    // Truncate text for display
    truncateText(text, maxLength = 100) {
        if (!text || text.length <= maxLength) return text;
        return text.substring(0, maxLength) + '...';
    }
};

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SupabaseClient;
} 