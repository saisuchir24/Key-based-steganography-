document.addEventListener('DOMContentLoaded', function() {
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const messageInput = form.querySelector('textarea[name="message"]');
            const passwordInput = form.querySelector('input[type="password"]');
            const fileInput = form.querySelector('input[type="file"]');
            
            if (messageInput && messageInput.value.length > 10000) {
                alert('Message must be 10000 characters or less.');
                e.preventDefault();
                return;
            }
            
            if (!passwordInput.value) {
                alert('Password is required.');
                e.preventDefault();
                return;
            }
            
            if (!fileInput.files[0]) {
                alert('Please select a file.');
                e.preventDefault();
                return;
            }
        });
    });
    
    // Optional: Add a subtle effect on file selection
    const fileInputs = document.querySelectorAll('input[type="file"]');
    fileInputs.forEach(input => {
        const label = input.previousElementSibling;
        if (label && label.getAttribute('data-original') === null) {
            label.setAttribute('data-original', label.textContent);
        }
        input.addEventListener('change', function() {
            const label = input.previousElementSibling;
            if (input.files[0]) {
                label.textContent = `Selected: ${input.files[0].name}`;
            } else {
                label.textContent = label.getAttribute('data-original') || 'Choose File';
            }
        });
    });
});
