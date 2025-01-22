import openai
import re

class LLMService:
    def __init__(self, api_key, api_base, api_version, deployment_name):
        openai.api_type = "azure"
        openai.api_base = api_base
        openai.api_version = api_version
        openai.api_key = api_key
        self.deployment_name = deployment_name

    def get_response(self, context, query):
        """Get response from LLM based on context and query"""
        try:
            response = openai.ChatCompletion.create(
                engine=self.deployment_name,
                messages=[
                    {
                        "role": "system", 
                        "content": "You are a helpful assistant that answers questions based on the provided document context."
                    },
                    {
                        "role": "user", 
                        "content": f"Context:\n{context}\n\nQuestion:\n{query}"
                    },
                ],
                temperature=0.7,
                max_tokens=800,
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error getting LLM response: {e}")
            return None

    def rank_chunks_with_llm(self, chunk_mapping, context_chunks, query, assistant_reply):
        """Have LLM rank the context chunks based on their relevance to the answer"""
        chunks_to_rank = []
        for chunk in context_chunks:
            chunk_text = chunk_mapping[chunk['chunk_id']]
            chunks_to_rank.append({
                'chunk_id': chunk['chunk_id'],
                'content': chunk_text,
                'initial_score': chunk['score']
            })

        ranking_prompt = f"""
Given the following question and your answer, please analyze these context chunks and rank them based on their relevance and importance to your answer. For each chunk, provide a score from 0-10 and explain why.

Question: {query}

Your Answer: {assistant_reply}

Context Chunks to Rank:
{'-' * 40}
"""

        for i, chunk in enumerate(chunks_to_rank, 1):
            ranking_prompt += f"\nChunk {i}:\n{chunk['content']}\n{'-' * 40}"

        try:
            response = openai.ChatCompletion.create(
                engine=self.deployment_name,
                messages=[
                    {
                        "role": "system", 
                        "content": "You are an analytical assistant that evaluates text relevance. Provide numerical scores and brief explanations for each chunk."
                    },
                    {
                        "role": "user", 
                        "content": ranking_prompt
                    }
                ],
                temperature=0.3,
                max_tokens=1000
            )

            analysis = response.choices[0].message.content
            scores = self._extract_scores(analysis, chunks_to_rank)
            ranked_chunks = self._combine_and_rank_scores(chunks_to_rank, scores)
            
            return [chunk['chunk_id'] for chunk in ranked_chunks]

        except Exception as e:
            print(f"Error in LLM chunk ranking: {e}")
            return [chunk['chunk_id'] for chunk in chunks_to_rank]

    def _extract_scores(self, analysis, chunks_to_rank):
        """Extract scores from LLM analysis"""
        scores = {}
        for i, chunk in enumerate(chunks_to_rank, 1):
            score_patterns = [
                rf"Chunk {i}:\s*(\d+)(?:/10)?",
                rf"Chunk {i}.*?score:\s*(\d+)",
                rf"Score for Chunk {i}:\s*(\d+)"
            ]
            
            for pattern in score_patterns:
                match = re.search(pattern, analysis, re.IGNORECASE)
                if match:
                    score = int(match.group(1))
                    scores[chunk['chunk_id']] = score / 10.0
                    break
            
            if chunk['chunk_id'] not in scores:
                scores[chunk['chunk_id']] = chunk['initial_score']
                
        return scores

    def _combine_and_rank_scores(self, chunks_to_rank, scores):
        """Combine LLM scores with initial similarity scores and rank chunks"""
        for chunk in chunks_to_rank:
            chunk['final_score'] = (
                0.7 * scores[chunk['chunk_id']] + 
                0.3 * chunk['initial_score']
            )
        
        return sorted(
            chunks_to_rank, 
            key=lambda x: x['final_score'], 
            reverse=True
        )