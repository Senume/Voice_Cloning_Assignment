# Voice Cloning Assignment
- - -

The work have utilised the pretrained model SV2TTS proposed in the paper "Transfer Learning from Speaker Verification to
Multispeaker Text-To-Speech Synthesis". Basic system consists of three components namely
1. Speaker Encoder -  Its purpose is to generate a fixed-dimensional embedding vector by analyzing a few seconds of reference speech from a target speaker.
2. equence-to-Sequence Synthesis Network - this network generates a mel spectrogram from input text with reference to target speakers embeddings.
3. Auto-regressive Vocoder Network - Converts the mel spectogram into waveform samples.

 The model can effectively transfer the knowledge of speaker variability learned by the discriminatively-trained speaker encoder to the multi-speaker text-to-speech task. As a result, it is capable of generating natural-sounding speech from speakers who were not seen during the training phase.

 ## **REQUIREMENTS**

 - Need to install ffmpeg for reading the audio files
 - Install PyTroch. Select the version which support for GPU (GPU is recommended), else CPU based also be used for the implementation.
 - Install the remaining dependencies given in the '''requirement.txt''' file

 ## **GETTING STARTED**

 