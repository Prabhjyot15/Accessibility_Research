import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import say from "say";
import { GlobalKeyboardListener } from "node-global-key-listener";

// Get the directory name of the current module
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Load steps from JSON file
const steps = JSON.parse(
  fs.readFileSync(
    path.join(__dirname, "./accessibility-guides/create-channel-private.json")
  )
).steps;

// Function to read out a step description using text-to-speech
const readStep = (step) => {
  return new Promise((resolve, reject) => {
    const voice = "Microsoft David Desktop"; // or 'Microsoft Zira Desktop'
    say.speak(step.description, voice, 1.0, (err) => {
      if (err) {
        console.error("Error speaking:", err);
        reject(err);
      } else {
        resolve();
      }
    });
  });
};

// Function to simulate keyboard input based on action type
const simulateAction = async (action) => {
  return new Promise((resolve, reject) => {
    const listener = new GlobalKeyboardListener();
    let success = false;
    let index = 0;

    const handleKeypress = (e, down) => {
      const pressedKey = e.name.toLowerCase();
      console.log(`Pressed key: ${pressedKey}`);

      // Normalize pressed key
      const normalizePressedKey = (key) => {
        switch (key) {
          case 'left ctrl':
          case 'right ctrl':
            return 'ctrl';
          case 'left shift':
          case 'right shift':
            return 'shift';
          case 'forward slash':
            return '/'; // Normalize "/" to "forward slash"
          default:
            return key.toLowerCase();
        }
      };

      const normalizedPressedKey = normalizePressedKey(pressedKey);

      // Check if the action type is 'string'
      if (action.type === 'string') {
        // Convert action value to lowercase for case insensitivity
        const expectedString = action.value.toLowerCase();
        
        // Match full expectedString only when finished entering it
        if (normalizedPressedKey === expectedString[index]) {
          index++;
          if (index === expectedString.length) {
            success = true;
            listener.stop();
            resolve(true);
          }
        } else {
          // Reset on incorrect key press
          index = 0;
        }
      } else if (action.type === 'keyboard') {
        // Check if the action type is 'keyboard' and handle key sequences
        const expectedKeys = action.keys.map(key => key.toLowerCase());
        if (normalizedPressedKey === expectedKeys[index]) {
          index++;
          if (index === expectedKeys.length) {
            success = true;
            listener.stop();
            resolve(true);
          }
        } else {
          // Reset on incorrect key press
          index = 0;
        }
      }
    };

    listener.addListener(handleKeypress);
    listener.start();

    if (action.type === 'string') {
      console.log(`Enter string: ${action.value}`);
    } else {
      console.log(`Press: ${action.keys.join(' + ')} (no Enter needed):`);
    }

    // Timeout to handle action timeout scenarios (adjust time as needed)
    setTimeout(() => {
      if (!success) {
        listener.stop();
        reject(new Error('Action timeout'));
      }
    }, 60000); // Adjust timeout value (in milliseconds) as per your requirement
  });
};

// Main function to run the tutorial
const runTutorial = async () => {
  try {
    for (let step of steps) {
      await readStep(step); // Read step description
      await simulateAction(step.action); // Simulate the action defined in JSON
      console.log('Step completed successfully.\n');
    }
    console.log('Tutorial completed.');
  } catch (error) {
    console.error("Error during tutorial:", error);
  }
};

// Start the tutorial
runTutorial();
