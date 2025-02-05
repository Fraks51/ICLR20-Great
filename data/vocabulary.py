import os
import random

import json

import tensorflow as tf
import sentencepiece as spm


class Vocabulary():
	def __init__(self, vocab_path, code_mode, ulm_model=None):
		self.vocab_path = vocab_path
		self.code_mode = code_mode
		if ulm_model is None and code_mode == "ULM":
			raise ValueError("Need to define --ulm for using ULM code representation")
		self.ulm_model = ulm_model
		self.load_vocab()
	
	def load_vocab(self):
		if self.code_mode == "ULM":
			self.sentence_piece = spm.SentencePieceProcessor(model_file=self.ulm_model)
			self.vocab_dim = sum(1 for _ in open(self.vocab_path, 'r')) + 1
		else:
			with open(self.vocab_path, encoding='utf-8') as f:
				subtokens = [l.rstrip() for l in f]
			self.i2w = {ix+1:w for ix, w in enumerate(subtokens)}
			self.i2w[0] = "<PAD>"
			self.w2i = {w: ix for ix, w in self.i2w.items()}
			self.vocab_dim = len(self.i2w)

			# Some data structures to split up sub-tokenization
			self.bpe_cache = {}
			self.bpe_lookup_dict = {}
			for token in self.w2i.keys():
				if token[:2] not in self.bpe_lookup_dict:
					self.bpe_lookup_dict[token[:2]] = set()
				self.bpe_lookup_dict[token[:2]].add(token)
	
	def translate(self, token, is_subtokenized=False):
		if self.code_mode == "single":
			tokens = "".join(filter(lambda x: x not in "\n\r`\'", token))
			tokens = tokens.replace("_", " ")
			return [self.lookup(t) for t in tokens.split()]
		elif self.code_mode == "BPE":
			return self.lookup(token) if is_subtokenized else [self.lookup(t) for t in self.tokenize(token)]
		elif self.code_mode == "ULM":
			return self.sentence_piece.encode_as_ids(token)
		else:
			raise ValueError("Unsupported mode of code representation.")

	def lookup(self, token):
		return self.w2i[token] if token in self.w2i else self.w2i["<PAD>"]  # Ignore truly unknown tokens; only happens when specific characters were never seen in training data.
	
	def tokenize(self, token):
		token += "#"  # Add terminal symbol first
		tokens = []
		ix = 0
		if token in self.bpe_cache:
			return self.bpe_cache[token]
		while ix < len(token):
			if ix == len(token) - 2:
				tokens.append(token[ix:])
				break
			else:
				candidates = self.bpe_lookup_dict.get(token[ix:ix+2], [])
				if not candidates:
					top_candidate = token[ix]
				else:
					# Only sub-tokens that match the next characters and don't leave the end-of-word marker left by itself
					candidates = [t for t in candidates if t == token[ix:ix+len(t)] and not len(token) == ix + len(t) + 1]
					if not candidates: top_candidate = token[ix]
					else: top_candidate = max(candidates, key=lambda e: len(e))
				tokens.append(top_candidate)
				ix += len(top_candidate)
		self.bpe_cache[token] = tokens
		return tokens