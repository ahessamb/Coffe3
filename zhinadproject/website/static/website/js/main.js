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

    // ========== TOAST NOTIFICATIONS ==========
    function showToast(message, type = 'success', options = {}) {
        const container = document.querySelector('[data-toast-container]');
        if (!container || !message) return;

        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.setAttribute('role', 'status');

        const body = document.createElement('div');
        body.className = 'toast-body';
        body.textContent = message;

        if (options.cartLink) {
            const link = document.createElement('a');
            link.href = options.cartLink;
            link.className = 'toast-action';
            link.textContent = 'مشاهده سبد خرید';
            body.appendChild(document.createElement('br'));
            body.appendChild(link);
        }

        const closeBtn = document.createElement('button');
        closeBtn.type = 'button';
        closeBtn.className = 'toast-close';
        closeBtn.setAttribute('aria-label', 'بستن');
        closeBtn.textContent = '×';

        toast.appendChild(body);
        toast.appendChild(closeBtn);
        container.appendChild(toast);

        requestAnimationFrame(() => toast.classList.add('toast-visible'));

        const dismiss = () => {
            toast.classList.remove('toast-visible');
            setTimeout(() => toast.remove(), 300);
        };

        const timeout = setTimeout(dismiss, options.duration || 4500);
        closeBtn.addEventListener('click', () => {
            clearTimeout(timeout);
            dismiss();
        });
    }

    function formatPrice(amount) {
        const value = Math.round(Number(amount) || 0);
        return value.toLocaleString('fa-IR') + ' تومان';
    }

    function updateCartBadge(count) {
        const badge = document.querySelector('[data-cart-count]');
        if (!badge) return;
        const itemCount = Number(count) || 0;
        badge.textContent = itemCount;
        badge.classList.toggle('cart-count--empty', itemCount === 0);
    }

    function getCsrfToken(form) {
        const input = form.querySelector('[name=csrfmiddlewaretoken]');
        return input ? input.value : '';
    }

    // ========== PRODUCT QUANTITY SELECTORS ==========
    function initProductQtySelectors() {
        document.querySelectorAll('.product-qty-form').forEach(form => {
            const input = form.querySelector('.qty-input');
            if (!input) return;

            form.querySelectorAll('[data-qty-action]').forEach(btn => {
                btn.addEventListener('click', () => {
                    const action = btn.getAttribute('data-qty-action');
                    const currentQty = parseInt(input.value, 10) || 1;
                    const maxQty = parseInt(input.getAttribute('max'), 10) || 99;
                    const minQty = parseInt(input.getAttribute('min'), 10) || 1;

                    if (action === 'increase' && currentQty < maxQty) {
                        input.value = currentQty + 1;
                    } else if (action === 'decrease' && currentQty > minQty) {
                        input.value = currentQty - 1;
                    }
                });
            });
        });
    }

    // ========== ADD TO CART (AJAX) ==========
    function initAddToCart() {
        document.querySelectorAll('[data-add-to-cart]').forEach(form => {
            form.addEventListener('submit', async (e) => {
                e.preventDefault();

                const submitBtn = form.querySelector('[type="submit"]');
                if (submitBtn) submitBtn.disabled = true;

                try {
                    const response = await fetch(form.action, {
                        method: 'POST',
                        headers: {
                            'X-Requested-With': 'XMLHttpRequest',
                            'X-CSRFToken': getCsrfToken(form),
                        },
                        body: new FormData(form),
                    });

                    const data = await response.json();

                    if (!response.ok || !data.success) {
                        showToast(data.message || 'افزودن به سبد خرید ناموفق بود.', 'error');
                        return;
                    }

                    updateCartBadge(data.cart_count);
                    const cartUrl = document.querySelector('.cart-icon')?.getAttribute('href') || '/cart/';
                    showToast(data.message, 'success', { cartLink: cartUrl });
                } catch (error) {
                    showToast('خطا در افزودن به سبد خرید. دوباره تلاش کنید.', 'error');
                } finally {
                    if (submitBtn) submitBtn.disabled = false;
                }
            });
        });
    }

    // ========== CART PAGE AJAX UPDATES ==========
    function initCartPage() {
        const cartPage = document.querySelector('.cart-page');
        if (!cartPage) return;

        async function updateCartItem(form, action) {
            const formData = new FormData(form);
            formData.set('action', action);

            const cartItem = form.closest('[data-cart-item]');
            const input = form.querySelector('.qty-input');

            try {
                const response = await fetch(form.action, {
                    method: 'POST',
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest',
                        'X-CSRFToken': getCsrfToken(form),
                    },
                    body: formData,
                });

                const data = await response.json();
                if (!data.success) {
                    showToast(data.message || 'به‌روزرسانی سبد خرید ناموفق بود.', 'error');
                    return;
                }

                updateCartBadge(data.cart_count);

                const totalEl = document.querySelector('[data-cart-total]');
                const countEl = document.querySelector('[data-cart-item-count]');
                if (totalEl) totalEl.textContent = formatPrice(data.total);
                if (countEl) countEl.textContent = data.total_quantity ?? data.cart_count;

                if (data.removed || data.cart_count === 0) {
                    if (cartItem) cartItem.remove();
                }

                if (data.cart_count === 0) {
                    window.location.reload();
                    return;
                }

                if (cartItem && data.item) {
                    if (input) input.value = data.item.quantity;
                    const subtotalEl = cartItem.querySelector('[data-cart-subtotal]');
                    if (subtotalEl) subtotalEl.textContent = formatPrice(data.item.subtotal);
                }
            } catch (error) {
                showToast('خطا در به‌روزرسانی سبد خرید.', 'error');
            }
        }

        document.querySelectorAll('[data-cart-update-form]').forEach(form => {
            const input = form.querySelector('.qty-input');

            form.querySelectorAll('[data-action]').forEach(btn => {
                btn.addEventListener('click', () => {
                    const action = btn.getAttribute('data-action');
                    updateCartItem(form, action);
                });
            });

            if (input) {
                input.addEventListener('change', () => {
                    const formData = new FormData(form);
                    formData.set('action', 'set');
                    formData.set('quantity', input.value);

                    fetch(form.action, {
                        method: 'POST',
                        headers: {
                            'X-Requested-With': 'XMLHttpRequest',
                            'X-CSRFToken': getCsrfToken(form),
                        },
                        body: formData,
                    })
                        .then(response => response.json())
                        .then(data => {
                            if (!data.success) {
                                showToast(data.message || 'به‌روزرسانی سبد خرید ناموفق بود.', 'error');
                                return;
                            }

                            updateCartBadge(data.cart_count);

                            const totalEl = document.querySelector('[data-cart-total]');
                            const countEl = document.querySelector('[data-cart-item-count]');
                            if (totalEl) totalEl.textContent = formatPrice(data.total);
                            if (countEl) countEl.textContent = data.total_quantity ?? data.cart_count;

                            const cartItem = form.closest('[data-cart-item]');
                            if (data.removed || data.cart_count === 0) {
                                if (cartItem) cartItem.remove();
                            }
                            if (data.cart_count === 0) {
                                window.location.reload();
                                return;
                            }
                            if (cartItem && data.item) {
                                input.value = data.item.quantity;
                                const subtotalEl = cartItem.querySelector('[data-cart-subtotal]');
                                if (subtotalEl) subtotalEl.textContent = formatPrice(data.item.subtotal);
                            }
                        })
                        .catch(() => showToast('خطا در به‌روزرسانی سبد خرید.', 'error'));
                });
            }
        });
    }

    // ========== CART FUNCTIONALITY (legacy qty buttons outside cart page) ==========
    function initCart() {
        // Handled by initProductQtySelectors and initCartPage
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
        initProductQtySelectors();
        initAddToCart();
        initCartPage();
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
