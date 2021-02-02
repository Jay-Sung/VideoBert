import argparse
import logging
import os
import random

import numpy as np
import spacy
from torch.nn.utils.rnn import pad_sequence
from torch.utils.data import DataLoader, RandomSampler
from tqdm import tqdm

from VideoBERT.data.VideoBertDataset import VideoBertDataset
from VideoBERT.train.custom_vid_transformer import VideoTransformer
from VideoBERT.train.model_utils import *

spacy_en = spacy.load('en')


def set_seed(args):
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    if args.n_gpu > 0:
        torch.cuda.manual_seed_all(args.seed)


def tokenize_en(text):
    """
    Tokenizes English text from a string into a list of strings
    """
    return [tok.text for tok in spacy_en.tokenizer(text)]


def text_next_tok_pred(args, model, tokenizer, sentence, max_len=50):
    model.eval()
    sentence = sentence[:,:10]
    sentence.insert(0, tokenizer.vocab.stoi[tokenizer.init_token])
    sentence.append(tokenizer.vocab.stoi[tokenizer.eos_token])
    print(sentence)
    for i in range(max_len):
        inp_tensor = torch.LongTensor(sentence).unsqueeze(0).to(args.device)
        tok_type_ids = torch.zeros_like(inp_tensor).long().to(args.device)
        attn_mask = (inp_tensor == 1).to(args.device)
        with torch.no_grad():
            output = model(
                text_input_ids=inp_tensor,
                text_token_type_ids=tok_type_ids,
                text_attention_mask=attn_mask,
            )
        pred = output[0].argmax(2)[:,-1].item()
        if pred == tokenizer.vocab.stoi[tokenizer.eos_token]:
            break
        sentence.insert(-1, pred)

    return ' '.join([tokenizer.vocab.itos[token] for token in sentence])


def video_next_tok_pred(args, model, tokenizer, vid_example, max_len=50):
    model.eval()
    sentence = vid_example[:, :3]
    sentence.insert(0, tokenizer.vocab.stoi[tokenizer.init_token])
    sentence.append(tokenizer.vocab.stoi[tokenizer.eos_token])
    print(sentence)
    for i in range(max_len):
        inp_tensor = torch.LongTensor(sentence).unsqueeze(0).to(args.device)
        tok_type_ids = torch.ones_like(inp_tensor).long().to(args.device)
        attn_mask = (inp_tensor == 1).to(args.device)
        with torch.no_grad():
            output = model(
                video_input_ids=inp_tensor,
                video_token_type_ids=tok_type_ids,
                video_attention_mask=attn_mask,
            )
        pred = output[0].argmax(2)[:,-1].item()
        if pred == tokenizer.vocab.stoi[tokenizer.eos_token]:
            break
        sentence.insert(-1, pred)

    return ' '.join(sentence)


def main(colab_args=None):
    if colab_args:
        args = colab_args
    else:
        parser = argparse.ArgumentParser()

        parser.add_argument(
            "--model_name_or_path",
            default=None,
            type=str,
            help="The model checkpoint for weights initialization. Leave None if you want to train a model from scratch.",
        )
        parser.add_argument(
            "--output_dir",
            type=str,
            required=True,
            help="The output directory where the checkpoint is.",
        )
        parser.add_argument(
            "--sentence",
            default=None,
            type=str,
            help="The sentence for inferencing the model"
        )
        parser.add_argument("--seed", type=int, default=42, help="random seed for initialization")
        args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    args.device = device
    args.n_gpu = 1

    set_seed(args)

    # setup tokenizer and model
    tokenizer = torch.load(os.path.join(args.output_dir, "tokenizer.pt"))
    eval_dataset = VideoBertDataset(tokenizer, build_tokenizer=False, data_path='eval_data.json')
    data_globals.config.vocab_size = len(tokenizer.vocab.itos) + 20736
    print("total vocab size of", len(tokenizer.vocab.itos) + 20736)

    # start from checkpoint
    print('### LOADING MODEL FROM CHECKPOINT:', args.model_name_or_path, '###')
    model = VideoTransformer.from_pretrained(config=data_globals.config, args=args)

    model.to(args.device)

    print("original examples")
    print(eval_dataset[0][0], eval_dataset[0][3])

    print(text_next_tok_pred(args, model, tokenizer, eval_dataset[0][0]))
    print(video_next_tok_pred(args, model, tokenizer, eval_dataset[0][3]))


if __name__ == "__main__":
    main()
