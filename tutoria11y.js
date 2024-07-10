const fs = require('fs');
const { join } = require('path');
const say = require('say');
const { GlobalKeyboardListener } = require('node-global-key-listener');

// Load steps from JSON file
const steps = JSON.parse(fs.readFileSync(join(__dirname, 'steps.json'))).steps;

// Function to read out a step description using text-to-speech
const readStep = async (step) => {
  return new Promise((resolve, reject) => {
    const voice = 'Microsoft David Desktop'; // or 'Microsoft Zira Desktop'
    say.speak(step.description, voice, 1.0, (err) => {
      if (err) {
        console.error('Error speaking:', err);
        reject(err);
      } else {
        resolve();
      }
    });
  });
};

const simulateKeyboardInput = async (keys) => {
  return new Promise((resolve, reject) => {
    let index = 0;

    const listener = new GlobalKeyboardListener();

    const handleKeypress = (e, down) => {
      console.log(
        `${e.name} ${e.state == "DOWN" ? "DOWN" : "UP"} [${e.rawKey._nameRaw}]`
      );

      const expectedKey = keys[index].toLowerCase();

      if (
        e.state == "DOWN" &&
        e.name.toLowerCase() === expectedKey ||
        (expectedKey === 'ctrl' && (down["LEFT CTRL"] || down["RIGHT CTRL"])) ||
        (expectedKey === 'shift' && (down["LEFT SHIFT"] || down["RIGHT SHIFT"]))
      ) {
        index++;
        if (index === keys.length) {
          listener.stop();
          resolve(true); 
        }
      } else {
        // Incorrect key pressed
        console.log(`Incorrect key pressed. Expected: ${keys[index].toUpperCase()}`);
        index = 0;
      }
    };

    listener.addListener(handleKeypress);
    listener.start();

    console.log(`Press: ${keys.join(' + ')} (no Enter needed):`);
  });
};

// Example usage
simulateKeyboardInput(['ctrl', 'shift', 'i']).then(result => {
  console.log('Input successful:', result);
}).catch(err => {
  console.error('Error:', err);
});

// Main function to run the tutorial
const runTutorial = async () => {
  try {
    for (let step of steps) {
      await readStep(step);

      const keys = step.action.split('+').map(key => key.trim()); // Split action into keys
      console.log(`Waiting for input: ${step.action}`);

      let userInput = await simulateKeyboardInput(keys);

      if (userInput) {
        console.log('Correct input!\n');
      } else {
        console.log(`Incorrect input. Expected: ${step.action}\n`);
        await readStep(step); // Repeat the step description
        await simulateKeyboardInput(keys); // Repeat the input simulation
      }
    }

    console.log('Tutorial completed.');
  } catch (error) {
    console.error('Error during tutorial:', error);
  }
};

// Start the tutorial
runTutorial();
