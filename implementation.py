import argparse
import os
from pathlib import Path
import warnings

import librosa
import numpy as np
import soundfile as sf
import torch

warnings.filterwarnings("ignore")

from src.encoder import inference as encoder
from src.encoder.params_model import model_embedding_size as speaker_embedding_size
from src.synthesizer.inference import Synthesizer
from src.utils.argutils import print_args
from src.utils.default_models import ensure_default_models
from src.vocoder import inference as vocoder


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("-e", "--enc_model_fpath", type=Path,
                        default="src/saved_models/default/encoder.pt",
                        help="Path to a saved encoder")
    
    parser.add_argument("-s", "--syn_model_fpath", type=Path,
                        default="src/saved_models/default/synthesizer.pt",
                        help="Path to a saved synthesizer")
    
    parser.add_argument("-v", "--voc_model_fpath", type=Path,
                        default="src/saved_models/default/vocoder.pt",
                        help="Path to a saved vocoder")
    
    parser.add_argument("--cpu", action="store_true", help=\
        "If True, processing is done on CPU, even when a GPU is available.")

    parser.add_argument("--seed", type=int, default=None, help=\
        "Optional random number seed value to make toolbox deterministic.")
    
    print('Displaying the settings')
    args = parser.parse_args()
    arg_dict = vars(args)
    print_args(args, parser)

    # Hide GPUs from Pytorch to force CPU processing
    if arg_dict.pop("cpu"):
        os.environ["CUDA_VISIBLE_DEVICES"] = "-1"

    print("Setting system configuration...\n")

    if torch.cuda.is_available():
        device_id = torch.cuda.current_device()
        gpu_properties = torch.cuda.get_device_properties(device_id)
        ## Print some environment information (for debugging purposes)
        print("Found %d GPUs available. Using GPU %d (%s) of compute capability %d.%d with "
            "%.1fGb total memory.\n" %
            (torch.cuda.device_count(),
            device_id,
            gpu_properties.name,
            gpu_properties.major,
            gpu_properties.minor,
            gpu_properties.total_memory / 1e9))
    else:
        print("Using CPU for inference.\n")

    ## Load the models one by one.
    print("Downloading and loadin the pretrained model")
    ensure_default_models(Path("src/saved_models"))
    encoder.load_model(args.enc_model_fpath)
    synthesizer = Synthesizer(args.syn_model_fpath)
    vocoder.load_model(args.voc_model_fpath)


    try:
        # Get the reference audio filepath
        message = "Reference voice: enter an audio filepath of a voice to be cloned (mp3, " \
                  "wav, m4a, flac, ...):\n"
        in_fpath = Path(input(message).replace("\"", "").replace("\'", ""))

        ## Computing the embedding
        # First, we load the wav using the function that the speaker encoder provides. This is
        # important: there is preprocessing that must be applied.

        # The following two methods are equivalent:
        # - Directly load from the filepath:
        preprocessed_wav = encoder.preprocess_wav(in_fpath)
        
        # - If the wav is already loaded:
        original_wav, sampling_rate = librosa.load(str(in_fpath))
        preprocessed_wav = encoder.preprocess_wav(original_wav, sampling_rate)
        print("Loaded file succesfully")
        # Then we derive the embedding. There are many functions and parameters that the
        # speaker encoder interfaces. These are mostly for in-depth research. You will typically
        # only use this function (with its default parameters):
        embed = encoder.embed_utterance(preprocessed_wav)
        print("Created the embedding")

        ## Generating the spectrogram
        text = input("Write a sentence (+-20 words) to be synthesized:\n")
        # If seed is specified, reset torch seed and force synthesizer reload
        if args.seed is not None:
            torch.manual_seed(args.seed)
            synthesizer = Synthesizer(args.syn_model_fpath)

        # The synthesizer works in batch, so you need to put your data in a list or numpy array
        texts = [text]
        embeds = [embed]
        # If you know what the attention layer alignments are, you can retrieve them here by
        # passing return_alignments=True
        specs = synthesizer.synthesize_spectrograms(texts, embeds)
        spec = specs[0]
        print("Created the mel spectrogram")
        ## Generating the waveform
        print("Synthesizing the waveform:")
        # If seed is specified, reset torch seed and reload vocoder
        if args.seed is not None:
            torch.manual_seed(args.seed)
            vocoder.load_model(args.voc_model_fpath)
        # Synthesizing the waveform is fairly straightforward. Remember that the longer the
        # spectrogram, the more time-efficient the vocoder.
        generated_wav = vocoder.infer_waveform(spec)

        ## Post-generation
        # There's a bug with sounddevice that makes the audio cut one second earlier, so we
        # pad it.
        generated_wav = np.pad(generated_wav, (0, synthesizer.sample_rate), mode="constant")
        # Trim excess silences to compensate for gaps in spectrograms (issue #53)
        generated_wav = encoder.preprocess_wav(generated_wav)

        # Saving the generated voice on the disk
        filename = input('\nEnter the filename to be saved as\n') + '.wav'
        os.chdir('output')
        sf.write(filename, generated_wav.astype(np.float32), synthesizer.sample_rate)
        os.chdir('..')

        print("\nSaved output as %s\n\n" % filename)

    except Exception as e:
        print("Caught exception: %s" % repr(e))
        print("Restarting\n")