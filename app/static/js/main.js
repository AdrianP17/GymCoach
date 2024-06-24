 // Script para mostrar y ocultar la ventana flotante
 document.getElementById('profile-link').addEventListener('click', function(event) {
    event.preventDefault();
    document.getElementById('profile-modal').style.display = 'block';
});

document.querySelector('.close-btn').addEventListener('click', function() {
    document.getElementById('profile-modal').style.display = 'none';    
});

window.addEventListener('click', function(event) {
    if (event.target === document.getElementById('profile-modal')) {
        document.getElementById('profile-modal').style.display = 'none';
    }
});
// Script para scrollear el chat
function scrollToBottom() {
    var chatContainer = document.getElementById("chat-container");
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

document.addEventListener("DOMContentLoaded", function() {
    scrollToBottom();
});