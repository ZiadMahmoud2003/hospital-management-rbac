document.addEventListener('DOMContentLoaded', function() {

    // Add your custom JavaScript here

    console.log('Hospital Theme Loaded');

    // Add animation to login button

    const loginBtn = document.getElementById('kc-login');

    if (loginBtn) {

        loginBtn.addEventListener('mouseenter', function() {

            this.style.transform = 'translateY(-1px)';

            this.style.boxShadow = '0 4px 12px rgba(16, 185, 129, 0.3)';

        });

        loginBtn.addEventListener('mouseleave', function() {

            this.style.transform = 'translateY(0)';

            this.style.boxShadow = 'none';

        });

    }

    // Add focus styles to inputs

    const inputs = document.querySelectorAll('input[type="text"], input[type="password"]');

    inputs.forEach(input => {

        input.addEventListener('focus', function() {

            this.style.borderColor = '#10b981';

            this.style.boxShadow = '0 0 0 3px rgba(16, 185, 129, 0.1)';

        });

        input.addEventListener('blur', function() {

            this.style.borderColor = '#d1d5db';

            this.style.boxShadow = 'none';

        });

    });

});
 