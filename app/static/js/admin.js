// Функція для тестування конфігурації з HTML блоками
async function testConfigWithBlocks() {
    const url = document.getElementById('platform-url').value;
    const titleBlock = document.getElementById('title-block').value;
    const reviewBlock = document.getElementById('review-block').value;
    
    try {
        const response = await fetch('/admin/platforms/test-config', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                url: url,
                title_block: titleBlock,
                review_block: reviewBlock
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            // Показуємо результат
            const resultArea = document.getElementById('config-result');
            resultArea.value = JSON.stringify(data.config, null, 2);
            showNotification('success', 'Конфігурацію успішно згенеровано');
        } else {
            showNotification('error', data.error || 'Помилка при генерації конфігурації');
        }
    } catch (error) {
        console.error('Error:', error);
        showNotification('error', 'Помилка при відправці запиту');
    }
}

// Функція для показу повідомлень
function showNotification(type, message) {
    const notification = document.getElementById('notification');
    notification.textContent = message;
    notification.className = `notification ${type}`;
    notification.style.display = 'block';
    
    setTimeout(() => {
        notification.style.display = 'none';
    }, 5000);
} 