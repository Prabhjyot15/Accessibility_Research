const { contextBridge, ipcRenderer } = require('electron');
const fs = require('fs');

// Expose IPC renderer to window object
contextBridge.exposeInMainWorld('electron', {
  send: (channel, data) => ipcRenderer.send(channel, data),
  receive: (channel, func) => {
    ipcRenderer.on(channel, (event, ...args) => func(...args));
  }
});

// Example of receiving data from main process
ipcRenderer.on('fromMain', (event, data) => {
  console.log('Received from main process:', data);
});
