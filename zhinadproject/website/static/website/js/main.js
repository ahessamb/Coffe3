/**
 * Zhinad - Main JavaScript Module
 * Handles interactive features: navigation, header scroll, messaging, forms
 */

(function() {
    'use strict';

    // ========== MOBILE NAVIGATION ==========
    function initMobileNav() {
        const navToggle = document.querySelector('[data-nav-toggle]');
        const navOverlay = document.querySelector('[data-nav-overlay]');
        const mobileNav = document.querySelector('[data-mobile-nav]');
        const body = document.body;

        if (!navToggle) return;

        const toggleNav = () => {
            const isOpen = body.classList.contains('nav-open');
            body.classList.toggle('nav-open');
            navToggle.setAttribute('aria-expanded', !isOpen);
        };

        const closeNav = () => {
            body.classList.remove('nav-open');
            navToggle.setAttribute('aria-expanded', 'false');
        };

        navToggle.addEventListener('click', toggleNav);

        if (navOverlay) {
            navOverlay.addEventListener('click', closeNav);
        }

        if (mobileNav) {
            const navLinks = mobileNav.querySelectorAll('a');
            navLinks.forEach(link => {
                link.addEventListener('click', closeNav);
            });
        }

        // Close nav on Escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && body.classList.contains('nav-open')) {
                closeNav();
            }
        });
    }

    // ========== HEADER SCROLL EFFECT ==========
    function initHeaderScroll() {
        const header = document.querySelector('.header');
        if (!header) return;

        let lastScrollTop = 0;
        const scrollThreshold = 5;

        window.addEventListener('scroll', () => {
            const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
            
            if (scrollTop > scrollThreshold) {
                header.classList.add('header-scrolled');
            } else {
                header.classList.remove('header-scrolled');
            }
            
            lastScrollTop = scrollTop;
        }, { passive: true });
    }

    // ========== MESSAGE DISMISSAL ==========
    function initMessages() {
        const messages = document.querySelectorAll('.alert');
        
        messages.forEach(message => {
            // Auto-dismiss after 5 seconds
            const timeout = setTimeout(() => {
                dismissMessage(message);
            }, 5000);

            // Allow click to dismiss
            message.addEventListener('click', () => {
                clearTimeout(timeout);
                dismissMessage(message);
            });
        });

        function dismissMessage(element) {
            element.style.animation = 'slideOutUp 0.3s ease';
            setTimeout(() => {
                element.remove();
            }, 300);
        }
    }

    // ========== FORM ENHANCEMENTS ==========
    function initForms() {
        // Number input keyboard behavior
        const numberInputs = document.querySelectorAll('input[type="number"]');
        numberInputs.forEach(input => {
            input.setAttribute('inputmode', 'numeric');
        });

        // Format numbers as user types (for currency fields)
        const currencyInputs = document.querySelectorAll('input[data-currency]');
        currencyInputs.forEach(input => {
            input.addEventListener('input', function() {
                if (this.value) {
                    this.value = this.value.replace(/[^0-9]/g, '');
                }
            });
        });

        // Add focus state to form fields
        const formControls = document.querySelectorAll('.form-input, .form-textarea, .form-select');
        formControls.forEach(control => {
            control.addEventListener('focus', function() {
                this.closest('.form-group')?.classList.add('is-focused');
            });

            control.addEventListener('blur', function() {
                this.closest('.form-group')?.classList.remove('is-focused');
            });
        });
    }

    // ========== CART FUNCTIONALITY ==========
    function initCart() {
        const cartButtons = document.querySelectorAll('.qty-btn');
        cartButtons.forEach(btn => {
            btn.addEventListener('click', function(e) {
                e.preventDefault();
                const form = this.closest('.quantity-form');
                if (form) {
                    const input = form.querySelector('.qty-input');
                    const isIncrease = this.textContent.trim() === '+';
                    const currentQty = parseInt(input.value) || 1;
                    const maxQty = parseInt(input.getAttribute('max')) || 99;

                    if (isIncrease && currentQty < maxQty) {
                        input.value = currentQty + 1;
                    } else if (!isIncrease && currentQty > 1) {
                        input.value = currentQty - 1;
                    }

                    // Trigger change event for form submission
                    input.dispatchEvent(new Event('change', { bubbles: true }));
                }
            });
        });
    }

    // ========== SMOOTH SCROLL FOR ANCHOR LINKS ==========
    function initSmoothScroll() {
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function(e) {
                const href = this.getAttribute('href');
                if (href === '#') return;

                const target = document.querySelector(href);
                if (target) {
                    e.preventDefault();
                    const headerHeight = document.querySelector('.header')?.offsetHeight || 70;
                    const targetPosition = target.offsetTop - headerHeight;
                    
                    window.scrollTo({
                        top: targetPosition,
                        behavior: 'smooth'
                    });
                }
            });
        });
    }

    // ========== IMAGE LAZY LOADING FALLBACK ==========
    function initLazyLoad() {
        if ('IntersectionObserver' in window) {
            const imageObserver = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const img = entry.target;
                        if (img.dataset.src) {
                            img.src = img.dataset.src;
                            img.removeAttribute('data-src');
                        }
                        imageObserver.unobserve(img);
                    }
                });
            }, {
                rootMargin: '50px'
            });

            document.querySelectorAll('img[data-src]').forEach(img => {
                imageObserver.observe(img);
            });
        }
    }

    // ========== INPUT VALIDATION FEEDBACK ==========
    function initValidation() {
        const form = document.querySelector('.checkout-form') || document.querySelector('form');
        if (!form) return;

        form.addEventListener('submit', function(e) {
            const inputs = this.querySelectorAll('.form-input, .form-textarea, .form-select');
            let isValid = true;

            inputs.forEach(input => {
                if (!input.checkValidity()) {
                    input.classList.add('is-invalid');
                    isValid = false;
                } else {
                    input.classList.remove('is-invalid');
                }
            });

            if (!isValid) {
                e.preventDefault();
                const firstInvalid = this.querySelector('.is-invalid');
                if (firstInvalid) {
                    firstInvalid.focus();
                    firstInvalid.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
            }
        });

        // Remove invalid class on input
        const inputs = document.querySelectorAll('.form-input, .form-textarea, .form-select');
        inputs.forEach(input => {
            input.addEventListener('input', function() {
                if (this.checkValidity()) {
                    this.classList.remove('is-invalid');
                }
            });
        });
    }

    // ========== QUANTITY INPUT IMPROVEMENTS ==========
    function initQuantityInputs() {
        const qtyInputs = document.querySelectorAll('.qty-input');
        qtyInputs.forEach(input => {
            input.addEventListener('change', function() {
                const max = parseInt(this.getAttribute('max')) || 99;
                const min = parseInt(this.getAttribute('min')) || 1;
                let value = parseInt(this.value) || min;

                if (value > max) value = max;
                if (value < min) value = min;

                this.value = value;
            });

            input.addEventListener('keydown', function(e) {
                const allowedKeys = ['Backspace', 'Delete', 'Tab', 'Escape', 'Enter', 'ArrowUp', 'ArrowDown'];
                if (!allowedKeys.includes(e.key) && !e.ctrlKey && !e.metaKey) {
                    if (!/[0-9]/.test(e.key)) {
                        e.preventDefault();
                    }
                }
            });
        });
    }

    // ========== ADAPTIVE IMAGE LOADING ==========
    function adaptiveImages() {
        if ('loading' in HTMLImageElement.prototype) return;

        const images = document.querySelectorAll('img[loading="lazy"]');
        const imageObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.style.backgroundImage = 'none';
                    imageObserver.unobserve(img);
                }
            });
        });

        images.forEach(img => imageObserver.observe(img));
    }

    // ========== TOUCH INTERACTIONS FOR MOBILE ==========
    function initTouchEnhancements() {
        // Add active state feedback
        const touchElements = document.querySelectorAll('.btn, .product-card, .blog-card, .cart-item');
        
        touchElements.forEach(element => {
            element.addEventListener('touchstart', function() {
                this.style.opacity = '0.95';
            });

            element.addEventListener('touchend', function() {
                this.style.opacity = '1';
            });
        });
    }

    // ========== INITIALIZE ALL ==========
    function init() {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', initAll);
        } else {
            initAll();
        }
    }

    function initAll() {
        initMobileNav();
        initHeaderScroll();
        initMessages();
        initForms();
        initCart();
        initSmoothScroll();
        initLazyLoad();
        initValidation();
        initQuantityInputs();
        adaptiveImages();
        initTouchEnhancements();

        // Log initialization in development
        if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
            console.log('✓ Zhinad UI initialized');
        }
    }

    init();
})();

// Add utility styles for smooth animations (injected CSS)
(function() {
    const style = document.createElement('style');
    style.textContent = `
        @keyframes slideOutUp {
            from {
                transform: translateY(0);
                opacity: 1;
            }
            to {
                transform: translateY(-20px);
                opacity: 0;
            }
        }
        
        .form-group.is-focused .form-input,
        .form-group.is-focused .form-textarea,
        .form-group.is-focused .form-select {
            border-color: var(--color-gold);
        }
        
        /* Smooth transitions for interactive elements */
        .btn { transition: all 0.25s ease; }
        .form-input, .form-textarea, .form-select { transition: all 0.25s ease; }
        .product-card, .blog-card { transition: all 0.25s ease; }
    `;
    document.head.appendChild(style);
})();
