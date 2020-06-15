const socket = new SockJS('http://152.118.148.95:15674/stomp');
const mqClient = Stomp.over(socket);
const path = window.location.pathname;
const baseQueueName = `/exchange/1706067626T/${path.substring(path.lastIndexOf('/') + 1)}.`;
let startTime = null;
let currentTime = moment();
let isFinished = false;
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
    isFinished = true;
    const secret = JSON.parse(message.body);
    const downloadButton = document.getElementById('downloadButton');
    downloadButton.setAttribute('href', `http://infralabs.cs.ui.ac.id:20068/${secret.fileName}?md5=${secret.md5}&expires=${secret.expires}`);
    downloadButton.classList.remove('disabled');
    const momentDuration = moment.duration(currentTime.diff(startTime));
    const timeDuration = document.getElementById('serviceDuration');
    timeDuration.innerText = 'Service has finished, took';
    const moreThanOneMinute = momentDuration.asSeconds() > 60;
    if (momentDuration.hours() > 0) {
        timeDuration.innerText += ` ${momentDuration.hours()} hour${momentDuration.hours() > 1 ? 's' : ''}`;
    }
    if (momentDuration.minutes() > 0) {
        timeDuration.innerText += ` ${momentDuration.minutes()} minute${momentDuration.minutes() > 1 ? 's' : ''}`;
    }
    timeDuration.innerText += ` ${moreThanOneMinute ? ' and' : ''}${momentDuration.seconds()} second${momentDuration.seconds() > 1 ? 's' : ''}.`;
};
const timeHandler = (message) => {
    const time = JSON.parse(message.body);
    if (startTime === null) {
        startTime = moment.unix(time.time);
    }
    if (!isFinished) {
        currentTime = moment.unix(time.time);
        const timeDisplay = document.getElementById('timeDisplay');
        timeDisplay.innerText = currentTime.from(startTime, true);
        const timeStartEl = document.getElementById('timeStart');
        if (timeStartEl.innerText === 'now') {
            timeStartEl.innerText = startTime.format('HH:mm:ss');
        }
    }
};
const connectHandler = () => {
    mqClient.subscribe(`${baseQueueName}download`, downloadProgressHandler);
    mqClient.subscribe(`${baseQueueName}compress`, compressProgressHandler);
    mqClient.subscribe(`${baseQueueName}secret`, secretUrlHandler);
    mqClient.subscribe('/exchange/1706067626_FANOUT', timeHandler);
};
const errorHandler = (error) => console.error(error);
if (window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') mqClient.debug = () => null;
mqClient.connect('0806444524', '0806444524', connectHandler, errorHandler, '/0806444524');
