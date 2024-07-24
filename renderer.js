const { ipcRenderer } = require('electron');
const fs = require('fs');
const path = require('path');

// Function to start the tutorial
const startTutorial = () => {
  const tutorialFile = path.join(__dirname, 'tutorial.json'); // Replace with the path to your tutorial file
  ipcRenderer.send('start-tutorial', tutorialFile);
};

// Function to fetch the accessibility tree
const fetchAccessibilityTree = () => {
  ipcRenderer.send('get-accessibility-tree');
};

// Function to fetch the UI tree from the .NET application
const fetchUIAutomationTree = () => {
  ipcRenderer.send('get-ui-tree');
};

// Handler for accessibility tree updates
ipcRenderer.on('accessibility-tree-updated', (event, treeData) => {
  console.log('Accessibility tree updated:', treeData);
  // Process and display the accessibility tree data as needed
});

// Handler for UI tree updates from .NET application
ipcRenderer.on('ui-tree-updated', (event, uiTreeData) => {
  console.log('UI tree updated:', uiTreeData);
  // Process and display the UI tree data as needed
});

// Event listener for the start tutorial button
document.getElementById('start-tutorial').addEventListener('click', () => {
  startTutorial();
});

// Event listener for the fetch accessibility tree button
document.getElementById('fetch-accessibility-tree').addEventListener('click', () => {
  fetchAccessibilityTree();
});

// Event listener for the fetch UI automation tree button
document.getElementById('fetch-ui-automation-tree').addEventListener('click', () => {
  fetchUIAutomationTree();
});
