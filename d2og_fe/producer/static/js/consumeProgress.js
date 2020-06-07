const socket = new SockJS('http://152.118.148.95:15674/stomp');
const mqClient = Stomp.over(socket);
const path = window.location.pathname;
const baseQueueName = `/exchange/1706067626T/${path.substring(path.lastIndexOf('/') + 1)}.`;
const downloadProgressHandler = (message) => {
    const progress = JSON.parse(message.body);
    const tdElement = document.getElementById(`download-${progress.index}`);
    tdElement.innerText = `${progress.progress === 100 ? 100.0.toFixed(1) : progress.progress.toFixed(2)}%`
};
const compressProgressHandler = (message) => {
    const progress = JSON.parse(message.body);
    const tdElement = document.getElementById('compress');
    tdElement.innerText = `${progress.progress === 100 ? 100.0.toFixed(1) : progress.progress.toFixed(2)}%`
};
const secretUrlHandler = (message) => {
    const secret = JSON.parse(message.body);
    const downloadButton = document.getElementById('downloadButton');
    downloadButton.setAttribute('href', `http://infralabs.cs.ui.ac.id:20068/${secret.fileName}?md5=${secret.md5}`);
    downloadButton.classList.remove('disabled');
};
const connectHandler = () => {
    mqClient.subscribe(`${baseQueueName}download`, downloadProgressHandler);
    mqClient.subscribe(`${baseQueueName}compress`, compressProgressHandler);
    mqClient.subscribe(`${baseQueueName}secret`, secretUrlHandler);
};
const errorHandler = (error) => console.error(error);
if (window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') mqClient.debug = () => null;
mqClient.connect('0806444524', '0806444524', connectHandler, errorHandler, '/0806444524');
