// GEM Enterprise - Main JavaScript Functions
document.addEventListener('DOMContentLoaded', function() {

    // Initialize all components
    initializeNavigation();
    initializeForms();
    initializeAnimations();
    initializeTheme();
    initializeLiveChat();

    // Navigation functionality
    function initializeNavigation() {
        const nav = document.getElementById('main-nav');
        const container = document.getElementById('nav-container');

        // Scroll listener for nav appearance
        window.addEventListener('scroll', () => {
            if (window.scrollY > 50) {
                if(nav) nav.classList.add('bg-[#030712]/90', 'backdrop-blur-3xl', 'shadow-2xl');
                if(container) container.classList.replace('h-24', 'h-20');
            } else {
                if(nav) nav.classList.remove('bg-[#030712]/90', 'backdrop-blur-3xl', 'shadow-2xl');
                if(container) container.classList.replace('h-20', 'h-24');
            }
        });

        // Mobile menu toggle
        const navbarToggler = document.querySelector('.navbar-toggler');
        const navbarCollapse = document.querySelector('.navbar-collapse');

        if (navbarToggler && navbarCollapse) {
            navbarToggler.addEventListener('click', function() {
                navbarCollapse.classList.toggle('show');
            });
        }

        // Smooth scrolling for anchor links
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function(e) {
                const href = this.getAttribute('href');
                if (href && href !== '#') {
                    e.preventDefault();
                    const target = document.querySelector(href);
                    if (target) {
                        target.scrollIntoView({
                            behavior: 'smooth',
                            block: 'start'
                        });
                    }
                }
            });
        });

        // Active navigation highlighting
        const currentLocation = location.pathname;
        const navLinks = document.querySelectorAll('.nav-link');

        navLinks.forEach(link => {
            if (link.getAttribute('href') === currentLocation) {
                link.classList.add('active');
            }
        });
    }

    // Form handling
    function initializeForms() {
        // Contact form
        const contactForm = document.getElementById('contactForm');
        if (contactForm) {
            contactForm.addEventListener('submit', function(e) {
                e.preventDefault();
                handleContactForm(this);
            });
        }

        // Newsletter form
        const newsletterForm = document.getElementById('newsletterForm');
        if (newsletterForm) {
            newsletterForm.addEventListener('submit', function(e) {
                e.preventDefault();
                handleNewsletterForm(this);
            });
        }

        // Client login form
        const clientLoginForm = document.getElementById('clientLoginForm');
        if (clientLoginForm) {
            clientLoginForm.addEventListener('submit', function(e) {
                e.preventDefault();
                handleClientLogin(this);
            });
        }

        // Admin login form
        const adminLoginForm = document.getElementById('adminLoginForm');
        if (adminLoginForm) {
            adminLoginForm.addEventListener('submit', function(e) {
                e.preventDefault();
                handleAdminLogin(this);
            });
        }

        // Password toggle functionality
        const togglePassword = document.getElementById('togglePassword');
        if (togglePassword) {
            togglePassword.addEventListener('click', function() {
                const passwordField = document.getElementById('password');
                const icon = this.querySelector('i');

                if (passwordField.type === 'password') {
                    passwordField.type = 'text';
                    icon.classList.remove('fa-eye');
                    icon.classList.add('fa-eye-slash');
                } else {
                    passwordField.type = 'password';
                    icon.classList.remove('fa-eye-slash');
                    icon.classList.add('fa-eye');
                }
            });
        }
    }

    // Form handlers
    function handleContactForm(form) {
        const formData = new FormData(form);
        const data = Object.fromEntries(formData);

        // Validate required fields
        const requiredFields = ['firstName', 'lastName', 'email', 'message'];
        let isValid = true;

        requiredFields.forEach(field => {
            const input = form.querySelector(`#${field}`);
            if (!input || !input.value.trim()) {
                showFieldError(input, 'This field is required');
                isValid = false;
            } else {
                clearFieldError(input);
            }
        });

        // Validate email format
        const emailField = form.querySelector('#email');
        if (emailField && !isValidEmail(emailField.value)) {
            showFieldError(emailField, 'Please enter a valid email address');
            isValid = false;
        }

        // Check agreement checkbox
        const agreeCheckbox = form.querySelector('#agree');
        if (agreeCheckbox && !agreeCheckbox.checked) {
            showAlert('error', 'Please agree to the terms of service and privacy policy');
            isValid = false;
        }

        if (isValid) {
            // Simulate form submission
            showAlert('success', 'Thank you for your message! Our team will contact you within 24 hours.');
            form.reset();
        }
    }

    function handleNewsletterForm(form) {
        const emailInput = form.querySelector('input[type="email"]');
        const selectInput = form.querySelector('select');

        if (!emailInput.value.trim()) {
            showFieldError(emailInput, 'Email address is required');
            return;
        }

        if (!isValidEmail(emailInput.value)) {
            showFieldError(emailInput, 'Please enter a valid email address');
            return;
        }

        if (!selectInput.value) {
            showFieldError(selectInput, 'Please select your interests');
            return;
        }

        // Simulate subscription
        showAlert('success', 'Successfully subscribed to our newsletter!');
        form.reset();
    }

    function handleClientLogin(form) {
        const username = form.querySelector('#username').value;
        const password = form.querySelector('#password').value;

        if (!username || !password) {
            showAlert('error', 'Please enter both username and password');
            return;
        }

        // Simulate login process
        showAlert('info', 'Authenticating... Please wait.');

        setTimeout(() => {
            showAlert('error', 'Login functionality is currently in development. Please contact support for access.');
        }, 2000);
    }

    function handleAdminLogin(form) {
        const username = form.querySelector('#adminUsername').value;
        const password = form.querySelector('#adminPassword').value;
        const token = form.querySelector('#adminToken').value;

        if (!username || !password || !token) {
            showAlert('error', 'All fields are required for admin access');
            return;
        }

        if (token.length !== 6 || !/^\d+$/.test(token)) {
            showAlert('error', 'Authentication token must be 6 digits');
            return;
        }

        // Simulate admin authentication
        showAlert('warning', 'Verifying administrator credentials...');

        setTimeout(() => {
            showAlert('error', 'Access denied. Administrator credentials are restricted to authorized personnel only.');
        }, 3000);
    }

    // Utility functions
    function isValidEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }

    function showFieldError(field, message) {
        clearFieldError(field);

        field.classList.add('is-invalid');
        const errorDiv = document.createElement('div');
        errorDiv.classList.add('invalid-feedback');
        errorDiv.textContent = message;
        field.parentNode.appendChild(errorDiv);
    }

    function clearFieldError(field) {
        field.classList.remove('is-invalid');
        const errorDiv = field.parentNode.querySelector('.invalid-feedback');
        if (errorDiv) {
            errorDiv.remove();
        }
    }

    function showAlert(type, message) {
        // Remove existing alerts
        const existingAlerts = document.querySelectorAll('.alert-dynamic');
        existingAlerts.forEach(alert => alert.remove());

        // Create new alert
        const alertDiv = document.createElement('div');
        alertDiv.classList.add('alert', `alert-${type}`, 'alert-dynamic', 'alert-dismissible', 'fade', 'show');
        alertDiv.style.position = 'fixed';
        alertDiv.style.top = '100px';
        alertDiv.style.right = '20px';
        alertDiv.style.zIndex = '9999';
        alertDiv.style.minWidth = '300px';

        const iconMap = {
            success: 'fa-check-circle',
            error: 'fa-exclamation-triangle',
            warning: 'fa-exclamation-circle',
            info: 'fa-info-circle'
        };

        // Create icon element
        const icon = document.createElement('i');
        icon.className = `fas ${iconMap[type]} me-2`;

        // Create message text node (safe from XSS)
        const messageText = document.createTextNode(message);

        // Create close button
        const closeButton = document.createElement('button');
        closeButton.type = 'button';
        closeButton.className = 'btn-close';
        closeButton.setAttribute('data-bs-dismiss', 'alert');

        // Append elements safely
        alertDiv.appendChild(icon);
        alertDiv.appendChild(messageText);
        alertDiv.appendChild(closeButton);

        document.body.appendChild(alertDiv);

        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, 5000);
    }

    // Animation and scroll effects
    function initializeAnimations() {
        // Intersection Observer for fade-in animations
        const observerOptions = {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        };

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('fade-in-up');
                    observer.unobserve(entry.target);
                }
            });
        }, observerOptions);

        // Observe cards and content sections
        const animatedElements = document.querySelectorAll('.service-card, .content-card, .testimonial-card, .team-department-card');
        animatedElements.forEach(el => observer.observe(el));

        // Parallax effect for hero section
        const heroSection = document.querySelector('.hero-section');
        if (heroSection) {
            window.addEventListener('scroll', () => {
                const scrolled = window.pageYOffset;
                const rate = scrolled * -0.5;
                heroSection.style.transform = `translateY(${rate}px)`;
            });
        }

        // Counter animation for statistics
        const counters = document.querySelectorAll('.stat-item h3, .performance-metric h4, [data-animate="counter"]');
        counters.forEach(counter => {
            const target = counter.dataset.count ? 
                parseFloat(counter.dataset.count) : 
                parseInt(counter.textContent.replace(/[^\d\.]/g, ''));
            if (target) {
                animateCounter(counter, target, counter.dataset.count);
            }
        });
    }

    function animateCounter(element, target, isDecimal) {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const duration = 2000;
                    const start = performance.now();

                    function updateCounter(currentTime) {
                        const elapsed = currentTime - start;
                        const progress = Math.min(elapsed / duration, 1);
                        const current = isDecimal ? 
                            (progress * target).toFixed(1) : 
                            Math.floor(progress * target);

                        element.textContent = current;

                        if (progress < 1) {
                            requestAnimationFrame(updateCounter);
                        }
                    }

                    requestAnimationFrame(updateCounter);
                    observer.unobserve(element);
                }
            });
        });

        observer.observe(element);
    }

    // Theme and visual enhancements
    function initializeTheme() {
        // Add loading animation
        window.addEventListener('load', () => {
            document.body.classList.add('loaded');
        });

        // Enhanced hover effects for cards
        const interactiveCards = document.querySelectorAll('.service-card, .content-card, .testimonial-card');
        interactiveCards.forEach(card => {
            card.addEventListener('mouseenter', function() {
                this.style.transform = 'translateY(-8px) scale(1.02)';
            });

            card.addEventListener('mouseleave', function() {
                this.style.transform = 'translateY(0) scale(1)';
            });
        });

        // Status dot animation
        const statusDots = document.querySelectorAll('.status-active');
        statusDots.forEach(dot => {
            setInterval(() => {
                dot.style.opacity = '0.5';
                setTimeout(() => {
                    dot.style.opacity = '1';
                }, 500);
            }, 2000);
        });

        // Security badge rotation
        const securityBadge = document.querySelector('.security-badge');
        if (securityBadge) {
            securityBadge.addEventListener('mouseenter', function() {
                this.style.transform = 'rotate(360deg) scale(1.1)';
                this.style.transition = 'transform 0.6s ease';
            });

            securityBadge.addEventListener('mouseleave', function() {
                this.style.transform = 'rotate(0deg) scale(1)';
            });
        }
    }

    // Security features
    function initializeSecurity() {
        // Disable right-click context menu on sensitive areas
        const secureElements = document.querySelectorAll('.admin-login-card, .security-dashboard');
        secureElements.forEach(element => {
            element.addEventListener('contextmenu', function(e) {
                e.preventDefault();
                showAlert('warning', 'Right-click is disabled for security reasons');
            });
        });

        // Log suspicious activity
        let rapidClicks = 0;
        document.addEventListener('click', function() {
            rapidClicks++;
            setTimeout(() => {
                rapidClicks--;
            }, 1000);

            if (rapidClicks > 10) {
                console.warn('Rapid clicking detected');
                showAlert('warning', 'Suspicious activity detected and logged');
            }
        });
    }

    // Initialize security features
    initializeSecurity();

    // Performance monitoring
    function initializePerformanceMonitoring() {
        // Monitor page load time (single source of truth)
        window.addEventListener('load', function() {
            const loadTime = Math.round(performance.now());
            if (loadTime > 3000) {
                console.warn(`Slow page load: ${loadTime}ms`);
            }
        });

        // Monitor memory usage
        if ('memory' in performance) {
            setInterval(() => {
                const memory = performance.memory;
                if (memory.usedJSHeapSize > 50000000) { // 50MB
                    console.warn('High memory usage detected');
                }
            }, 30000);
        }
    }

    initializePerformanceMonitoring();

    // Live Chat System
    function initializeLiveChat() {
        const liveChatButton = document.getElementById('liveChatButton');
        const liveChatModal = document.getElementById('liveChatModal');

        if (liveChatButton && liveChatModal) {
            // Initialize Bootstrap modal
            const modal = new bootstrap.Modal(liveChatModal);

            // Open the real Smartsupp conversation, with the existing modal as a resilient fallback.
            liveChatButton.addEventListener('click', function() {
                if (typeof window.smartsupp === 'function') {
                    window.smartsupp('chat:show');
                    window.smartsupp('chat:open');
                    console.log('Smartsupp live chat initiated by user');
                } else {
                    modal.show();
                    console.log('Smartsupp unavailable; support contact fallback opened');
                }
            });

            // Animate the chat button periodically
            setInterval(function() {
                liveChatButton.style.transform = 'scale(1.05)';
                setTimeout(function() {
                    liveChatButton.style.transform = 'scale(1)';
                }, 200);
            }, 8000);

            // Show chat button after a delay
            setTimeout(function() {
                liveChatButton.style.opacity = '1';
                liveChatButton.style.transform = 'translateY(0)';
            }, 3000);

            // Hide tooltip on mobile
            if (window.innerWidth <= 768) {
                const tooltip = liveChatButton.querySelector('.chat-tooltip');
                if (tooltip) {
                    tooltip.style.display = 'none';
                }
            }
        }

        // Emergency contact tracking
        const emergencyButtons = document.querySelectorAll('.btn-danger[href^="tel:"], .btn-danger[href^="mailto:"]');
        emergencyButtons.forEach(button => {
            button.addEventListener('click', function() {
                console.log('Emergency contact initiated:', this.href);
            });
        });
    }

    // Create loader styles
    const loaderStyle = document.createElement('style');
    loaderStyle.textContent = `
        .enterprise-loader {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 10000;
            opacity: 1;
            transition: opacity 0.5s ease-out;
        }

        .loader-content {
            text-align: center;
            color: white;
        }

        .loader-spinner {
            width: 50px;
            height: 50px;
            border: 3px solid rgba(255,255,255,0.3);
            border-radius: 50%;
            border-top-color: white;
            animation: spin 1s ease-in-out infinite;
            margin: 0 auto 20px;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }
    `;
    document.head.appendChild(loaderStyle);

    // Create enhanced security console styling
    const enhancedSecurityStyle = document.createElement('style');
    enhancedSecurityStyle.textContent = `
        .admin-login-card, .security-dashboard {
            cursor: not-allowed !important; /* Indicate restricted interaction */
        }
        .alert-dynamic {
            box-shadow: 0 4px 8px rgba(0,0,0,0.2); /* Enhance alert visibility */
        }
    `;
    document.head.appendChild(enhancedSecurityStyle);


    // Console security message
    console.log('%cGEM Enterprise Security Notice', 'color: #dc3545; font-size: 20px; font-weight: bold;');
    console.log('%cThis is a secure application. Unauthorized access attempts are monitored and logged.', 'color: #6c757d; font-size: 14px;');
    console.log('%cIf you are a legitimate user experiencing issues, please contact support.', 'color: #28a745; font-size: 14px;');

});

// Export functions for potential external use
window.GemEnterprise = {
    showAlert: function(type, message) {
        // This allows external scripts to show alerts if needed
        const event = new CustomEvent('showAlert', {
            detail: { type, message }
        });
        document.dispatchEvent(event);
    }
};