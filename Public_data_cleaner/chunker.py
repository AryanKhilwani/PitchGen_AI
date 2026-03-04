import json
import tiktoken


class SmartChunker:
    def __init__(self, max_tokens=2000, overlap_tokens=200):
        self.max_tokens = max_tokens
        self.overlap = overlap_tokens
        # Use a standard encoding (cl100k_base is used by GPT-4/Gemini models)
        self.tokenizer = tiktoken.get_encoding("cl100k_base")

    def count_tokens(self, text):
        return len(self.tokenizer.encode(text))

    def create_chunks(self, cleaned_data):
        """
        Input: List of dicts [{'url': '...', 'clean_text': '...'}]
        Output: List of dicts [{'url': '...', 'chunk_id': 1, 'text': '...'}]
        """
        all_chunks = []

        for entry in cleaned_data:
            url = entry["url"]
            text = entry["clean_text"]

            # Split by double newline to respect paragraph boundaries
            paragraphs = text.split("\n\n")

            current_chunk_tokens = 0
            current_chunk_paragraphs = []

            for p in paragraphs:
                p_tokens = self.count_tokens(p)

                # If a single paragraph is massive, we must split it (rare, but safe to handle)
                if p_tokens > self.max_tokens:
                    # Logic to split massive paragraphs could go here,
                    # but for now we'll append it and force a chunk break.
                    pass

                if current_chunk_tokens + p_tokens > self.max_tokens:
                    # 1. Finalize current chunk
                    chunk_text = "\n\n".join(current_chunk_paragraphs)
                    all_chunks.append({"url": url, "text": chunk_text})

                    # 2. Start new chunk with overlap
                    # Keep the last few paragraphs to maintain context
                    overlap_tokens_count = 0
                    new_start_paragraphs = []
                    for prev_p in reversed(current_chunk_paragraphs):
                        overlap_tokens_count += self.count_tokens(prev_p)
                        new_start_paragraphs.insert(0, prev_p)
                        if overlap_tokens_count >= self.overlap:
                            break

                    current_chunk_paragraphs = new_start_paragraphs
                    current_chunk_tokens = overlap_tokens_count

                # Add paragraph to current buffer
                current_chunk_paragraphs.append(p)
                current_chunk_tokens += p_tokens

            # Add the final leftover chunk
            if current_chunk_paragraphs:
                all_chunks.append(
                    {"url": url, "text": "\n\n".join(current_chunk_paragraphs)}
                )

        return all_chunks


# Usage
# chunker = SmartChunker()
# chunks = chunker.create_chunks(cleaned_output)
# print(f"Created {len(chunks)} chunks.")
