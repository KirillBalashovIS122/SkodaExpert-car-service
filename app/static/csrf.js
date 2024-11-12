function addCSRFToken() {
    var csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
    document.querySelectorAll('form').forEach(function(form) {
        var input = document.createElement('input');
        input.type = 'hidden';
        input.name = 'csrf_token';
        input.value = csrfToken;
        form.appendChild(input);
    });
}

document.addEventListener('DOMContentLoaded', addCSRFToken);