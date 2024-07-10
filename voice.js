const say = require('say');

say.getInstalledVoices((err, voices) => {
  if (err) {
    return console.error(err);
  }
  console.log(voices);
});
