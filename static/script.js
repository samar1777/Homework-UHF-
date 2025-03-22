window.onload = function() {
    // Check if popup has been shown before
    if (!localStorage.getItem('disclaimerShown')) {
        document.getElementById('disclaimer-popup').style.display = 'flex';
    }
};

function closePopup() {
    document.getElementById('disclaimer-popup').style.display = 'none';
    if (document.getElementById('dont-show-again').checked) {
        localStorage.setItem('disclaimerShown', 'true');
    }
}

document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('searchInput');
    const cards = document.querySelectorAll('.subject-card, .chapter-card');

    if (searchInput && cards) {
        searchInput.addEventListener('input', function(e) {
            const searchTerm = e.target.value.toLowerCase();

            cards.forEach(card => {
                const text = card.querySelector('h2').textContent.toLowerCase();
                if (text.includes(searchTerm)) {
                    card.style.display = 'block';
                } else {
                    card.style.display = 'none';
                }
            });
        });
    }
});
