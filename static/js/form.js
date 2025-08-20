// Extracted from templates/form.html
// ... JS code will be placed here ... 

// Country codes data with flags
const countryCodes = [
    { name: 'United States', code: '+1', flag: '🇺🇸', iso: 'US', placeholder: '(555) 123-4567' },
    { name: 'Canada', code: '+1', flag: '🇨🇦', iso: 'CA', placeholder: '(555) 123-4567' },
    { name: 'United Kingdom', code: '+44', flag: '🇬🇧', iso: 'GB', placeholder: '20 1234 5678' },
    { name: 'Australia', code: '+61', flag: '🇦🇺', iso: 'AU', placeholder: '412 345 678' },
    { name: 'Germany', code: '+49', flag: '🇩🇪', iso: 'DE', placeholder: '151 12345678' },
    { name: 'France', code: '+33', flag: '🇫🇷', iso: 'FR', placeholder: '6 12 34 56 78' },
    { name: 'Spain', code: '+34', flag: '🇪🇸', iso: 'ES', placeholder: '612 34 56 78' },
    { name: 'Italy', code: '+39', flag: '🇮🇹', iso: 'IT', placeholder: '312 345 6789' },
    { name: 'Mexico', code: '+52', flag: '🇲🇽', iso: 'MX', placeholder: '55 1234 5678' },
    { name: 'Brazil', code: '+55', flag: '🇧🇷', iso: 'BR', placeholder: '11 91234-5678' },
    { name: 'Argentina', code: '+54', flag: '🇦🇷', iso: 'AR', placeholder: '11 1234-5678' },
    { name: 'Japan', code: '+81', flag: '🇯🇵', iso: 'JP', placeholder: '90-1234-5678' },
    { name: 'China', code: '+86', flag: '🇨🇳', iso: 'CN', placeholder: '138 0013 8000' },
    { name: 'India', code: '+91', flag: '🇮🇳', iso: 'IN', placeholder: '98765 43210' },
    { name: 'Russia', code: '+7', flag: '🇷🇺', iso: 'RU', placeholder: '912 345-67-89' },
    { name: 'South Korea', code: '+82', flag: '🇰🇷', iso: 'KR', placeholder: '10-1234-5678' },
    { name: 'Netherlands', code: '+31', flag: '🇳🇱', placeholder: '6 12345678' },
    { name: 'Belgium', code: '+32', flag: '🇧🇪', placeholder: '470 12 34 56' },
    { name: 'Sweden', code: '+46', flag: '🇸🇪', placeholder: '70-123 45 67' },
    { name: 'Norway', code: '+47', flag: '🇳🇴', placeholder: '412 34 567' },
    { name: 'Denmark', code: '+45', flag: '🇩🇰', placeholder: '20 12 34 56' },
    { name: 'Finland', code: '+358', flag: '🇫🇮', placeholder: '41 2345678' },
    { name: 'Poland', code: '+48', flag: '🇵🇱', placeholder: '512 345 678' },
    { name: 'Switzerland', code: '+41', flag: '🇨🇭', placeholder: '78 123 45 67' },
    { name: 'Austria', code: '+43', flag: '🇦🇹', placeholder: '664 123456' },
    { name: 'Portugal', code: '+351', flag: '🇵🇹', placeholder: '912 345 678' },
    { name: 'Greece', code: '+30', flag: '🇬🇷', placeholder: '691 234 5678' },
    { name: 'Turkey', code: '+90', flag: '🇹🇷', placeholder: '532 123 4567' },
    { name: 'Israel', code: '+972', flag: '🇮🇱', placeholder: '50-123-4567' },
    { name: 'UAE', code: '+971', flag: '🇦🇪', placeholder: '50 123 4567' },
    { name: 'Saudi Arabia', code: '+966', flag: '🇸🇦', placeholder: '51 234 5678' },
    { name: 'South Africa', code: '+27', flag: '🇿🇦', placeholder: '71 123 4567' },
    { name: 'Egypt', code: '+20', flag: '🇪🇬', placeholder: '100 123 4567' },
    { name: 'Nigeria', code: '+234', flag: '🇳🇬', placeholder: '802 123 4567' },
    { name: 'Kenya', code: '+254', flag: '🇰🇪', placeholder: '712 123456' },
    { name: 'Singapore', code: '+65', flag: '🇸🇬', placeholder: '8123 4567' },
    { name: 'Malaysia', code: '+60', flag: '🇲🇾', placeholder: '12-345 6789' },
    { name: 'Thailand', code: '+66', flag: '🇹🇭', placeholder: '81 234 5678' },
    { name: 'Indonesia', code: '+62', flag: '🇮🇩', placeholder: '812-345-678' },
    { name: 'Philippines', code: '+63', flag: '🇵🇭', placeholder: '905 123 4567' },
    { name: 'Vietnam', code: '+84', flag: '🇻🇳', placeholder: '91 234 56 78' },
    { name: 'New Zealand', code: '+64', flag: '🇳🇿', placeholder: '21 123 4567' },
    { name: 'Ireland', code: '+353', flag: '🇮🇪', placeholder: '85 123 4567' },
    { name: 'Czech Republic', code: '+420', flag: '🇨🇿', placeholder: '601 123 456' },
    { name: 'Hungary', code: '+36', flag: '🇭🇺', placeholder: '20 123 4567' },
    { name: 'Romania', code: '+40', flag: '🇷🇴', placeholder: '712 345 678' },
    { name: 'Ukraine', code: '+380', flag: '🇺🇦', placeholder: '50 123 4567' },
    { name: 'Chile', code: '+56', flag: '🇨🇱', placeholder: '9 1234 5678' },
    { name: 'Colombia', code: '+57', flag: '🇨🇴', placeholder: '321 123 4567' },
    { name: 'Peru', code: '+51', flag: '🇵🇪', placeholder: '912 345 678' },
    { name: 'Venezuela', code: '+58', flag: '🇻🇪', placeholder: '412-1234567' }
];

// Phone number formatting functions for different countries
const phoneFormatters = {
    '+1': (value) => {
        // US/Canada format: (555) 123-4567
        if (value.length <= 3) return `(${value}`;
        if (value.length <= 6) return `(${value.substring(0, 3)}) ${value.substring(3)}`;
        return `(${value.substring(0, 3)}) ${value.substring(3, 6)}-${value.substring(6, 10)}`;
    },
    '+44': (value) => {
        // UK format: 20 1234 5678
        if (value.length <= 2) return value;
        if (value.length <= 6) return `${value.substring(0, 2)} ${value.substring(2)}`;
        return `${value.substring(0, 2)} ${value.substring(2, 6)} ${value.substring(6, 10)}`;
    },
    '+49': (value) => {
        // Germany format: 151 12345678
        if (value.length <= 3) return value;
        return `${value.substring(0, 3)} ${value.substring(3)}`;
    },
    '+33': (value) => {
        // France format: 6 12 34 56 78
        const parts = [];
        for (let i = 0; i < value.length; i += 2) {
            if (i === 0) {
                parts.push(value.substring(i, i + 1));
                i--;
            } else {
                parts.push(value.substring(i, i + 2));
            }
        }
        return parts.join(' ');
    },
    // Default formatter for other countries
    'default': (value) => value
};

// Initialize country code dropdowns
function initializePhoneInputs() {
    const phoneContainers = document.querySelectorAll('[data-phone-container]');
    
    phoneContainers.forEach(container => {
        const countrySelect = container.querySelector('[data-country-select]');
        const countryFlag = container.querySelector('[data-country-flag]');
        const countryCode = container.querySelector('[data-country-code]');
        const dropdown = container.querySelector('.country-code-dropdown');
        const searchInput = container.querySelector('[data-country-search]');
        const optionsContainer = container.querySelector('[data-country-options]');
        const phoneInput = container.querySelector('[data-phone-input]');
        
        let selectedCountry = countryCodes[0]; // Default to US
        
        // Populate country options
        function renderCountries(searchTerm = '') {
            const filtered = countryCodes.filter(country => 
                country.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                country.code.includes(searchTerm)
            );
            
            // Check if emoji is supported
            const isEmojiSupported = () => {
                const canvas = document.createElement('canvas');
                const ctx = canvas.getContext('2d');
                ctx.fillText('🇺🇸', -2, -2);
                return ctx.getImageData(0, 0, 1, 1).data[3] > 0;
            };
            
            const useEmoji = isEmojiSupported();
            
            optionsContainer.innerHTML = filtered.map(country => `
                <div class="country-option ${country.code === selectedCountry.code ? 'selected' : ''}" 
                     data-country-code="${country.code}">
                    ${useEmoji 
                        ? `<span class="country-flag">${country.flag}</span>`
                        : `<span class="country-iso">${country.iso || country.name.substring(0, 2).toUpperCase()}</span>`
                    }
                    <span class="country-name">${country.name}</span>
                    <span class="country-code">${country.code}</span>
                </div>
            `).join('');
            
            // Add click handlers to options
            optionsContainer.querySelectorAll('.country-option').forEach(option => {
                option.addEventListener('click', () => {
                    const code = option.dataset.countryCode;
                    selectedCountry = countryCodes.find(c => c.code === code);
                    updateSelectedCountry();
                    closeDropdown();
                });
            });
        }
        
        // Update selected country display
        function updateSelectedCountry() {
            // Check if emoji is supported
            const isEmojiSupported = () => {
                const canvas = document.createElement('canvas');
                const ctx = canvas.getContext('2d');
                ctx.fillText('🇺🇸', -2, -2);
                return ctx.getImageData(0, 0, 1, 1).data[3] > 0;
            };
            
            if (isEmojiSupported()) {
                countryFlag.textContent = selectedCountry.flag;
                countryFlag.className = 'country-flag';
            } else {
                countryFlag.textContent = selectedCountry.iso || selectedCountry.name.substring(0, 2).toUpperCase();
                countryFlag.className = 'country-iso';
            }
            
            countryCode.textContent = selectedCountry.code;
            phoneInput.placeholder = selectedCountry.placeholder;
            
            // Clear and reformat phone number if needed
            if (phoneInput.value) {
                formatPhoneNumber(phoneInput, selectedCountry.code);
            }
        }
        
        // Format phone number based on country
        function formatPhoneNumber(input, countryCode) {
            let value = input.value.replace(/\D/g, '');
            const formatter = phoneFormatters[countryCode] || phoneFormatters['default'];
            input.value = formatter(value);
        }
        
        // Toggle dropdown
        function toggleDropdown() {
            const isOpen = container.classList.contains('dropdown-open');
            closeAllDropdowns();
            if (!isOpen) {
                container.classList.add('dropdown-open');
                searchInput.value = '';
                renderCountries();
                searchInput.focus();
            }
        }
        
        // Close dropdown
        function closeDropdown() {
            container.classList.remove('dropdown-open');
        }
        
        // Close all dropdowns
        function closeAllDropdowns() {
            document.querySelectorAll('[data-phone-container]').forEach(c => {
                c.classList.remove('dropdown-open');
            });
        }
        
        // Event listeners
        countrySelect.addEventListener('click', (e) => {
            e.preventDefault();
            toggleDropdown();
        });
        
        searchInput.addEventListener('input', (e) => {
            renderCountries(e.target.value);
        });
        
        searchInput.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                closeDropdown();
            }
        });
        
        phoneInput.addEventListener('input', function(e) {
            formatPhoneNumber(this, selectedCountry.code);
        });
        
        phoneInput.addEventListener('paste', function(e) {
            e.preventDefault();
            const pastedText = (e.clipboardData || window.clipboardData).getData('text');
            this.value = pastedText;
            formatPhoneNumber(this, selectedCountry.code);
        });
        
        phoneInput.addEventListener('keypress', function(e) {
            const char = String.fromCharCode(e.which);
            if (!/[0-9]/.test(char) && e.which !== 8 && e.which !== 46) {
                e.preventDefault();
            }
        });
        
        // Initialize
        renderCountries();
        updateSelectedCountry();
        
        // Format existing values on page load
        if (phoneInput.value) {
            // If value already has country code, extract it
            const existingValue = phoneInput.value;
            const countryMatch = countryCodes.find(c => existingValue.startsWith(c.code));
            if (countryMatch) {
                selectedCountry = countryMatch;
                phoneInput.value = existingValue.substring(countryMatch.code.length);
                updateSelectedCountry();
            }
            formatPhoneNumber(phoneInput, selectedCountry.code);
        }
    });
    
    // Close dropdowns when clicking outside
    document.addEventListener('click', (e) => {
        if (!e.target.closest('[data-phone-container]')) {
            document.querySelectorAll('[data-phone-container]').forEach(c => {
                c.classList.remove('dropdown-open');
            });
        }
    });
}

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', function() {
    initializePhoneInputs();
});

// Mobile menu functionality
function toggleMobileMenu() {
    const sidebar = document.getElementById('tabsSidebar');
    const overlay = document.querySelector('.sidebar-overlay');
    const menuButton = document.querySelector('.mobile-menu-toggle');
    
    sidebar.classList.toggle('active');
    overlay.classList.toggle('active');
    
    // Update menu icon
    const icon = menuButton.querySelector('.material-icons');
    icon.textContent = sidebar.classList.contains('active') ? 'close' : 'menu';
}

function closeMobileMenu() {
    const sidebar = document.getElementById('tabsSidebar');
    const overlay = document.querySelector('.sidebar-overlay');
    const menuButton = document.querySelector('.mobile-menu-toggle');
    
    sidebar.classList.remove('active');
    overlay.classList.remove('active');
    
    // Reset menu icon
    const icon = menuButton.querySelector('.material-icons');
    icon.textContent = 'menu';
}

// Tab switching functionality
function switchTab(tabName) {
    // Update URL without page reload
    const url = new URL(window.location);
    url.searchParams.set('active_tab', tabName);
    window.history.pushState({}, '', url);

    // Hide all tab contents
    const allTabs = document.querySelectorAll('.tab-content');
    allTabs.forEach(tab => {
        tab.classList.remove('active');
    });

    // Remove active class from all tab buttons
    const allButtons = document.querySelectorAll('.tab-button');
    allButtons.forEach(button => {
        button.classList.remove('active');
    });

    // Show selected tab content with a slight delay for smooth transition
    setTimeout(() => {
        const selectedTab = document.getElementById(tabName + '-tab');
        if (selectedTab) {
            selectedTab.classList.add('active');
            
            // Reset animations for form sections and groups
            const formSections = selectedTab.querySelectorAll('.form-section');
            const formGroups = selectedTab.querySelectorAll('.form-group');
            const buttonGroup = selectedTab.querySelector('.button-group');
            
            // Remove animation classes temporarily
            formSections.forEach(section => {
                section.style.animation = 'none';
            });
            formGroups.forEach(group => {
                group.style.animation = 'none';
            });
            if (buttonGroup) {
                buttonGroup.style.animation = 'none';
            }
            
            // Force reflow
            void selectedTab.offsetWidth;
            
            // Re-add animations
            formSections.forEach((section, index) => {
                section.style.animation = `slideUp 0.6s ease forwards`;
                section.style.animationDelay = `${0.1 + index * 0.1}s`;
            });
            formGroups.forEach((group, index) => {
                group.style.animation = `fadeInUp 0.5s ease forwards`;
                group.style.animationDelay = `${0.1 + index * 0.05}s`;
            });
            if (buttonGroup) {
                buttonGroup.style.animation = `fadeIn 0.6s ease forwards`;
                buttonGroup.style.animationDelay = `0.5s`;
            }

            // Prefill the newly activated tab if we have shipment data
            try {
                if (window.__shipmentPrefill && typeof window.__shipmentPrefill.prefill === 'function') {
                    window.__shipmentPrefill.prefill(tabName);
                }
            } catch (_) { /* noop */ }
        }
    }, 100);

    // Add active class to clicked button
    const clickedButton = document.querySelector(`[onclick="switchTab('${tabName}')"]`);
    if (clickedButton) {
        clickedButton.classList.add('active');
    }

    // Close mobile menu after tab selection
    if (window.innerWidth <= 768) {
        closeMobileMenu();
    }

    // Scroll to top on mobile
    if (window.innerWidth <= 768) {
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }
}

// Handle browser back/forward buttons
window.addEventListener('popstate', () => {
    const url = new URL(window.location);
    const tabName = url.searchParams.get('active_tab') || 'default';
    switchTab(tabName);
});

function fillTestData() {
    // Get current date and time
    const now = new Date();
    const futureDate = new Date(now.getTime() + (24 * 60 * 60 * 1000)); // Tomorrow
    const pastDate = new Date(now.getTime() - (2 * 60 * 60 * 1000)); // 2 hours ago
    
    // Format dates for datetime-local input
    const formatDate = (date) => {
        return date.toISOString().slice(0, 16); // Format: YYYY-MM-DDThh:mm
    };

    // Get active tab
    const activeTab = document.querySelector('.tab-content.active').id;

    // Test data for different forms
    const testDataByForm = {
        'default-tab': {
            load_id: `LD-${Math.floor(Math.random() * 1000)}`,
            carrier_name: "ABC Logistics Inc.",
            contact_name: "John Smith",
            contact_phone: "5551234567",
            purpose: "Ask driver the name, confirm load id and confirm phone number",
            scheduled_pickup_time: formatDate(now),
            scheduled_delivery_time: formatDate(futureDate),
            origin_address: "123 Pickup St, Los Angeles, CA 90001",
            destination_address: "456 Delivery Ave, San Francisco, CA 94105",
            last_known_status: "In Transit",
            last_check_call_time: formatDate(pastDate),
            notes: "Test load - High priority shipment\nDriver prefers text updates\nDelivery requires lift gate"
        },
        'at-pickup-tab': {
            pickup_load_id: `LD-${Math.floor(Math.random() * 1000)}`,
            pickup_contact_phone: "5559876543",
            pickup_trucker_name: "Mike Johnson",
            pickup_address: "500 Warehouse Blvd, Chicago, IL 60601 - Appointment at 10:00 AM",
            driver_empty: "Y",
            driver_type: "otr",
            tractor_number: "T-4521",
            trailer_number: "TR-8976",
            required_equipment: "53ft dry van, load bars, straps",
            preferred_comms: "text",
            tracking_on: "Y",
            scheduled_drop_time: formatDate(futureDate)
        },
        'pickup-complete-tab': {
            pc_load_id: `LD-${Math.floor(Math.random() * 1000)}`,
            pc_contact_phone: "5552345678",
            pc_trucker_name: "Sarah Williams",
            actual_pickup_time: formatDate(pastDate),
            bol_verified: "Y",
            commodity_description: "Electronics - 24 pallets",
            next_stop_location: "Dallas, TX",
            scheduled_eta: formatDate(futureDate),
            accessorials_needed: "None required"
        },
        'in-transit-tab': {
            it_load_id: `LD-${Math.floor(Math.random() * 1000)}`,
            it_contact_phone: "5553456789",
            it_trucker_name: "Robert Davis",
            current_location: "Oklahoma City, OK",
            remaining_miles: "206",
            driver_tracking: "Y",
            delay_reason: "none"
        },
        'at-drop-tab': {
            ad_load_id: `LD-${Math.floor(Math.random() * 1000)}`,
            ad_contact_phone: "5554567890",
            ad_trucker_name: "James Wilson",
            receiver_name: "XYZ Distribution Center",
            receiver_address: "789 Delivery Rd, Dallas, TX 75201",
            arrival_time: formatDate(now),
            dock_number: "Door 42",
            lumper_needed: "Y",
            lumper_amount: "$150",
            payment_method: "Comcheck",
            osd_observed: "N"
        },
        'delivered-tab': {
            del_load_id: `LD-${Math.floor(Math.random() * 1000)}`,
            del_contact_phone: "5555678901",
            del_trucker_name: "Maria Garcia",
            empty_time: formatDate(now),
            pod_uploaded: "Y",
            lumper_receipt: "Y",
            final_osd: "N",
            osd_notes: "All items delivered in good condition"
        },
        'request-pod-tab': {
            pod_load_id: `LD-${Math.floor(Math.random() * 1000)}`,
            pod_contact_phone: "5553219876",
            pod_trucker_name: "David Thompson",
            delivery_date: formatDate(pastDate),
            upload_method: "app",
            reminder_attempt: "1"
        }
    };

    // Get test data for active form
    const testData = testDataByForm[activeTab] || {};

    // Populate form fields
    Object.keys(testData).forEach(fieldName => {
        const element = document.getElementById(fieldName);
        if (element) {
            element.value = testData[fieldName];
            // Trigger input event for phone numbers to format them
            if (element.classList.contains('phone-input')) {
                element.dispatchEvent(new Event('input', { bubbles: true }));
            }
        }
    });

    // Close mobile menu if open
    if (window.innerWidth <= 768) {
        closeMobileMenu();
    }
}

// Handle window resize
let resizeTimer;
window.addEventListener('resize', () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => {
        if (window.innerWidth > 768) {
            // Reset mobile menu state on desktop
            const sidebar = document.getElementById('tabsSidebar');
            const overlay = document.querySelector('.sidebar-overlay');
            sidebar.classList.remove('active');
            overlay.classList.remove('active');
        }
    }, 250);
});

// Prevent body scroll when mobile menu is open
document.addEventListener('DOMContentLoaded', () => {
    const overlay = document.querySelector('.sidebar-overlay');
    overlay.addEventListener('transitionend', () => {
        if (overlay.classList.contains('active')) {
            document.body.style.overflow = 'hidden';
        } else {
            document.body.style.overflow = '';
        }
    });
});

// Handle form submission
document.addEventListener('DOMContentLoaded', () => {
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', (e) => {
            // Process phone numbers before submission
            const phoneContainers = form.querySelectorAll('[data-phone-container]');
            phoneContainers.forEach(container => {
                const phoneInput = container.querySelector('[data-phone-input]');
                const countryCodeElement = container.querySelector('[data-country-code]');
                const countryCodeInput = container.querySelector('[data-country-code-input]');
                
                if (phoneInput && countryCodeElement && countryCodeInput) {
                    // Update the hidden country code field with current selected country code
                    countryCodeInput.value = countryCodeElement.textContent;
                    
                    // Keep phone number as-is (don't merge with country code)
                    // console.log('Country Code:', countryCodeInput.value);
                    // console.log('Phone Number:', phoneInput.value);
                }
            });
            
            // Show loading state on submit button
            const submitBtn = form.querySelector('.submit-btn');
            if (submitBtn) {
                const originalContent = submitBtn.innerHTML;
                submitBtn.innerHTML = '<span class="material-icons" style="animation: spin 1s linear infinite;">refresh</span> Processing...';
                submitBtn.disabled = true;
                
                // Add spinning animation
                const style = document.createElement('style');
                style.textContent = '@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }';
                document.head.appendChild(style);
            }
        });
    });
});

// Character counter functionality
document.addEventListener('DOMContentLoaded', function() {
    const textarea = document.getElementById('feedbackTextarea');
    const charCounter = document.getElementById('charCounter');
    const maxLength = 1600;

    if (!textarea || !charCounter) return;

    function updateCharCounter() {
        const currentLength = textarea.value.length;
        charCounter.textContent = `${currentLength}/${maxLength} characters`;

        // Update counter color based on length
        charCounter.classList.remove('near-limit', 'at-limit');
        if (currentLength >= maxLength) {
            charCounter.classList.add('at-limit');
        } else if (currentLength >= maxLength * 0.9) { // When 90% full
            charCounter.classList.add('near-limit');
        }
    }

    // Add event listeners
    textarea.addEventListener('input', updateCharCounter);
    textarea.addEventListener('keyup', updateCharCounter);
    textarea.addEventListener('paste', function(e) {
        setTimeout(updateCharCounter, 0);
    });

    // Initialize counter
    updateCharCounter();
}); 

// -------- Prefill from shipment JSON based on job_id & active_tab ---------
(function() {
    function getQueryParam(name) {
        const params = new URLSearchParams(window.location.search);
        return params.get(name);
    }

    function toDatetimeLocal(value) {
        if (!value) return '';
        try {
            const d = new Date(value);
            if (Number.isNaN(d.getTime())) return '';
            return d.toISOString().slice(0, 16);
        } catch (_) {
            return '';
        }
    }

    function setValue(id, val) {
        const el = document.getElementById(id);
        if (!el || val === undefined || val === null) return;
        el.value = String(val);
        if (el.classList.contains('phone-input')) {
            el.dispatchEvent(new Event('input', { bubbles: true }));
        }
    }

    function first(arr) {
        return Array.isArray(arr) && arr.length ? arr[0] : null;
    }

    function last(arr) {
        return Array.isArray(arr) && arr.length ? arr[arr.length - 1] : null;
    }

    function prefillForTab(payload, activeTab) {
        if (!payload) return;
        const pu = first(payload.pickUps);
        const dof = first(payload.dropOffs);
        const dol = last(payload.dropOffs);
        const fm = (payload.job || {}).fleetManager || {};
        const load = payload.load || {};

        const puContactPhone = (pu && pu.primaryContact && pu.primaryContact.phoneNumber) ? pu.primaryContact.phoneNumber : '';
        const dofContactPhone = (dof && dof.primaryContact && dof.primaryContact.phoneNumber) ? dof.primaryContact.phoneNumber : '';
        const fallbackPhone = fm.phoneNumber || '';
        const firstDropCityState = (dof && dof.location) ? [dof.location.city, dof.location.stateAbbr].filter(Boolean).join(', ') : '';
        const lastContactAddress = (payload.lastContact && payload.lastContact.fullAddress) ? payload.lastContact.fullAddress : '';

        if (activeTab === 'default') {
            setValue('load_id', payload.loadId ?? payload.load_id ?? '');
            setValue('carrier_name', (fm.company && fm.company.name) || fm.fullName || '');
            setValue('contact_name', fm.fullName || '');
            setValue('contact_phone', fm.phoneNumber || '');
            setValue('scheduled_pickup_time', toDatetimeLocal(pu?.startDate || pu?.startDateLocal));
            setValue('scheduled_delivery_time', toDatetimeLocal(dof?.startDate || dof?.startDateLocal));
            setValue('origin_address', pu?.location?.fullAddress || '');
            setValue('destination_address', dof?.location?.fullAddress || '');
            setValue('last_known_status', payload.status || payload.loadStatus || '');
            setValue('last_check_call_time', toDatetimeLocal(payload.lastContact?.dateTime));
            // Optional transfer not auto-set for default
        }

        if (activeTab === 'at-pickup') {
            setValue('pickup_load_id', payload.loadId ?? payload.load_id ?? '');
            setValue('pickup_contact_phone', fm.phoneNumber || '');
            setValue('pickup_trucker_name', fm.fullName || '');
            setValue('pickup_address', pu?.location?.fullAddress || '');
            setValue('scheduled_drop_time', toDatetimeLocal(dof?.startDate || dof?.startDateLocal));
            setValue('pickup_transfer_call_to', puContactPhone || fallbackPhone);
        }

        if (activeTab === 'pickup-complete') {
            setValue('pc_load_id', payload.loadId ?? payload.load_id ?? '');
            setValue('pc_contact_phone', fm.phoneNumber || '');
            setValue('pc_trucker_name', fm.fullName || '');
            setValue('actual_pickup_time', toDatetimeLocal(pu?.startDate || pu?.startDateLocal));
            setValue('scheduled_eta', toDatetimeLocal(dof?.startDate || dof?.startDateLocal));
            setValue('pc_transfer_call_to', dofContactPhone || fallbackPhone);
            setValue('commodity_description', load.commodity || '');
            setValue('next_stop_location', firstDropCityState);
        }

        if (activeTab === 'in-transit') {
            setValue('it_load_id', payload.loadId ?? payload.load_id ?? '');
            setValue('it_contact_phone', fm.phoneNumber || '');
            setValue('it_trucker_name', fm.fullName || '');
            setValue('it_transfer_call_to', dofContactPhone || fallbackPhone);
            setValue('current_location', lastContactAddress || '');
        }

        if (activeTab === 'at-drop') {
            setValue('ad_load_id', payload.loadId ?? payload.load_id ?? '');
            setValue('ad_contact_phone', fm.phoneNumber || '');
            setValue('ad_trucker_name', fm.fullName || '');
            setValue('receiver_address', dof?.location?.fullAddress || '');
            setValue('arrival_time', toDatetimeLocal(dof?.startDate || dof?.startDateLocal));
            setValue('ad_transfer_call_to', dofContactPhone || fallbackPhone);
            setValue('receiver_name', dof?.location?.name || '');
        }

        if (activeTab === 'delivered') {
            setValue('del_load_id', payload.loadId ?? payload.load_id ?? '');
            setValue('del_contact_phone', fm.phoneNumber || '');
            setValue('del_trucker_name', fm.fullName || '');
            setValue('empty_time', toDatetimeLocal(dol?.endDate || dol?.startDate || dol?.startDateLocal));
            setValue('del_transfer_call_to', dofContactPhone || fallbackPhone);
        }

        if (activeTab === 'request-pod') {
            setValue('pod_load_id', payload.loadId ?? payload.load_id ?? '');
            setValue('pod_contact_phone', fm.phoneNumber || '');
            setValue('pod_trucker_name', fm.fullName || '');
            setValue('delivery_date', toDatetimeLocal(dol?.endDate || dol?.startDate || dol?.startDateLocal));
            setValue('pod_transfer_call_to', dofContactPhone || fallbackPhone);
        }
    }

    window.__shipmentPrefill = {
        _payload: null,
        _fetching: false,
        async init(jobId, tab) {
            if (!jobId) return;
            if (this._payload || this._fetching) {
                if (this._payload && tab) prefillForTab(this._payload, tab);
                return;
            }
            try {
                this._fetching = true;
                const res = await fetch(`/shipments/data/${encodeURIComponent(jobId)}`, { credentials: 'same-origin' });
                if (!res.ok) return;
                const json = await res.json();
                this._payload = json?.data?.payload || json?.payload || null;
                if (this._payload && tab) prefillForTab(this._payload, tab);
            } catch (e) {
                console.warn('Init prefill failed', e);
            } finally {
                this._fetching = false;
            }
        },
        async prefill(tab) {
            const jobId = getQueryParam('job_id');
            if (!jobId) return;
            if (!this._payload) {
                await this.init(jobId, tab);
                return;
            }
            prefillForTab(this._payload, tab);
        }
    };

    document.addEventListener('DOMContentLoaded', () => {
        const jobId = getQueryParam('job_id');
        const activeTab = (new URL(window.location.href)).searchParams.get('active_tab') || 'default';
        if (jobId) {
            window.__shipmentPrefill.init(jobId, activeTab);
        }
    });
})();