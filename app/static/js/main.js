// Автоматичне закриття flash повідомлень
document.addEventListener('DOMContentLoaded', function() {
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.classList.remove('show');
            setTimeout(() => alert.remove(), 150);
        }, 5000);
    });
});

// Підтвердження видалення
function confirmDelete(message = 'Ви впевнені?') {
    return confirm(message);
}

// Форматування дати
function formatDate(dateString) {
    const options = { year: 'numeric', month: 'long', day: 'numeric' };
    return new Date(dateString).toLocaleDateString('uk-UA', options);
}

// Форматування рейтингу в зірочки
function formatRating(rating) {
    const fullStar = '★';
    const emptyStar = '☆';
    const stars = ''.padStart(Math.floor(rating), fullStar).padEnd(5, emptyStar);
    return `<span class="text-warning">${stars}</span> (${rating.toFixed(1)})`;
}

// Копіювання в буфер обміну
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(
        () => alert('Скопійовано в буфер обміну!'),
        () => alert('Помилка при копіюванні')
    );
}

// Валідація форм
function validateForm(form) {
    const requiredFields = form.querySelectorAll('[required]');
    let isValid = true;

    requiredFields.forEach(field => {
        if (!field.value.trim()) {
            field.classList.add('is-invalid');
            isValid = false;
        } else {
            field.classList.remove('is-invalid');
        }
    });

    return isValid;
}

// Обробка помилок API
function handleApiError(error) {
    console.error('API Error:', error);
    alert('Помилка при виконанні запиту. Спробуйте пізніше.');
}

// Анімація завантаження
function showLoading(button) {
    const originalText = button.innerHTML;
    button.disabled = true;
    button.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Завантаження...';
    return () => {
        button.disabled = false;
        button.innerHTML = originalText;
    };
}

function generateConfig() {
    const url = document.getElementById('config_url').value;
    const titleBlock = document.getElementById('config_title_block').value;
    const reviewBlock = document.getElementById('config_review_block').value;

    if (!url || !titleBlock || !reviewBlock) {
        showError('Будь ласка, заповніть всі поля');
        return;
    }

    // Показуємо індикатор завантаження
    const button = document.querySelector('#generateConfigModal .btn-primary');
    const resetLoading = showLoading(button);

    fetch('/admin/platforms/generate-config', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            url: url,
            title_block: titleBlock,
            review_block: reviewBlock
        })
    })
    .then(response => response.json())
    .then(data => {
        resetLoading(); // Прибираємо індикатор завантаження
        if (data.success) {
            document.getElementById('config_result').value = JSON.stringify(data.config, null, 2);
        } else {
            showError(data.error || 'Помилка при генерації конфігурації');
        }
    })
    .catch(error => {
        resetLoading(); // Прибираємо індикатор завантаження
        console.error('Error:', error);
        showError('Помилка при відправці запиту');
    });
}

// Функція для показу помилки
function showError(message) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'alert alert-danger alert-dismissible fade show';
    errorDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    document.querySelector('.modal-body').insertBefore(errorDiv, document.querySelector('#generateConfigForm'));
    
    // Автоматично приховуємо повідомлення через 5 секунд
    setTimeout(() => {
        errorDiv.classList.remove('show');
        setTimeout(() => errorDiv.remove(), 150);
    }, 5000);
}

document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('extractForm');
    if (!form) return; // Код виконується лише на дашборді

    const urlInput = document.getElementById('url');
    const submitBtn = document.getElementById('extractBtn');
    const loadingModal = new bootstrap.Modal(document.getElementById('loadingModal'));

    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        loadingModal.show();
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Обробка...';

        let redirected = false;

        try {
            const response = await fetch('/review/extract', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify({
                    url: urlInput.value
                })
            });

            if (response.status === 401) {
                redirected = true;
                loadingModal.hide();
                window.location.href = '/login?next=' + encodeURIComponent(window.location.pathname);
                return;
            }

            const contentType = response.headers.get('content-type');
            if (!contentType || !contentType.includes('application/json')) {
                redirected = true;
                loadingModal.hide();
                window.location.href = '/login?next=' + encodeURIComponent(window.location.pathname);
                return;
            }

            const data = await response.json();

            if (data && data.error && data.error === 'login_required') {
                redirected = true;
                loadingModal.hide();
                window.location.href = '/login?next=' + encodeURIComponent(window.location.pathname);
                return;
            }

            if (!response.ok) {
                throw new Error(data.error || 'Помилка при витягуванні відгуків');
            }

            if (data.error) {
                throw new Error(data.error);
            }

            if (data.extraction_id) {
                window.location.href = '/review/extraction/' + data.extraction_id;
            } else {
                throw new Error('Не вдалося отримати ID витягу');
            }

        } catch (error) {
            loadingModal.hide();
            if (!redirected) {
                alert(error.message || 'Помилка при витягуванні відгуків');
            }
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerHTML = '<i class="fas fa-download"></i> Витягти відгуки';
        }
    });
}); 