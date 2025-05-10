// for the constant changing of image, and video

const mediaElements = document.querySelectorAll('#mediaContainer img, #mediaContainer video');
console.log(mediaElements);
let currentIndex = 0;

function switchMedia() {
    mediaElements.forEach(element=>{
        element.classList.remove('active');
    });

    currentIndex = (currentIndex + 1) % mediaElements.length;
    mediaElements[currentIndex].classList.add('active');
}

setInterval(switchMedia, 5000);

mediaElements[0].classList.add('active');