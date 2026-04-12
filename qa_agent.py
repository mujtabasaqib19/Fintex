"""
Command-line Q&A agent for interacting with the pipeline.
Reads from existing data in Supabase + Qdrant and answers questions.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.reasoning import ReasoningEngine, AnswerSynthesizer
from src.retrieval import QueryRouter
from config.settings import get_settings


class QAAgent:
    """
    Question-Answering agent.
    
    Reads from existing database/vector store and provides answers.
    No ingestion - only retrieval and reasoning.
    """
    
    def __init__(self):
        """Initialize the Q&A agent."""
        print("🤖 Initializing Q&A Agent...")
        
        try:
            self.settings = get_settings()
            self.router = QueryRouter()
            self.reasoning_engine = ReasoningEngine()
            self.synthesizer = AnswerSynthesizer()
            
            print("✅ Agent ready!\n")
        except Exception as e:
            print(f"❌ Error initializing agent: {e}")
            sys.exit(1)
    
    def ask(self, query: str, use_reasoning: bool = True, format: str = "detailed") -> dict:
        """
        Ask a question and get an answer.
        
        Args:
            query: User's question
            use_reasoning: Whether to use full ToT reasoning (slower but better)
            format: "detailed", "brief", or "bullet"
            
        Returns:
            Answer dictionary
        """
        print(f"\n💭 Question: {query}")
        print("=" * 70)
        
        try:
            if use_reasoning:
                print("🔍 Using Tree of Thought reasoning...")
                # Full reasoning pipeline
                reasoning_result = self.reasoning_engine.reason(query)
                answer = self.synthesizer.synthesize(reasoning_result, format=format)
            else:
                print("🔍 Using simple retrieval...")
                # Simple retrieval
                evidence = self.reasoning_engine.reason_simple(query)
                answer = self.synthesizer.synthesize_simple(
                    query=query,
                    documents=evidence.get("document_evidence", []),
                    timeseries=evidence.get("timeseries_evidence", []),
                    stock_market=evidence.get("stock_market_evidence", []),  # Agent 3 data
                    format=format
                )
            
            return answer
        except Exception as e:
            print(f"❌ Error: {e}")
            return {"error": str(e)}
    
    def display_answer(self, answer: dict):
        """Display the answer in a formatted way."""
        if "error" in answer:
            print(f"\n❌ {answer['error']}")
            return
        
        print("\n" + "=" * 70)
        print("📝 ANSWER:")
        print("=" * 70)
        print(answer.get("answer", "No answer generated"))
        
        print("\n" + "-" * 70)
        confidence = answer.get("confidence", {})
        print(f"🎯 Confidence: {confidence.get('level', 'unknown').upper()}")
        sources = answer.get("sources", [])
        
        # Calculate web search count
        web_count = sum(1 for s in sources if s.get("source_type") == "Live Web Search")
        db_doc_count = getattr(confidence, "get", lambda k,d: 0)('document_count', 0) - web_count
        db_doc_count = max(0, db_doc_count) # Just in case
        
        print(f"   📄 Database Documents: {db_doc_count}")
        if web_count > 0:
            print(f"   🌐 Live Web Search Results: {web_count}")
            
        print(f"   📊 Data Points: {confidence.get('timeseries_count', 0)}")
        
        # Show stock market count if present
        stock_count = confidence.get('stock_market_count', 0)
        if stock_count > 0:
            print(f"   📈 Stock Market Data: {stock_count}")
        
        if sources:
            print(f"\n📚 Sources ({len(sources)}):")
            for idx, source in enumerate(sources[:7], 1):  # Show max 7
                if source.get("type") == "document":
                    if source.get("source_type") == "Live Web Search":
                        print(f"   {idx}. 🌐 {source.get('title', 'Untitled')}")
                    else:
                        print(f"   {idx}. 📄 {source.get('title', 'Untitled')}")
                    
                    if source.get("url"):
                        print(f"      🔗 {source['url']}")
                elif source.get("type") == "stock_market":
                    print(f"   {idx}. 📈 {source.get('symbol', '')} - {source.get('source', 'PSX')}")
                else:
                    print(f"   {idx}. 📊 {source.get('series_id', '')} [{source.get('provider', '')}]")
        
        print("=" * 70)
    
    def interactive_mode(self):
        """Run in interactive mode."""
        print("\n" + "=" * 70)
        print("🤖 DATA ANALYST Q&A AGENT - INTERACTIVE MODE")
        print("=" * 70)
        print("\nCommands:")
        print("  - Type your question to get an answer")
        print("  - '/simple <question>' for simple mode (faster)")
        print("  - '/brief <question>' for brief answer")
        print("  - '/bullet <question>' for bullet points")
        print("  - '/help' for help")
        print("  - '/quit' or '/exit' to quit")
        print("\n" + "=" * 70)
        
        while True:
            try:
                query = input("\n❓ You: ").strip()
                
                if not query:
                    continue
                
                # Handle commands
                if query.lower() in ['/quit', '/exit', 'quit', 'exit']:
                    print("\n👋 Goodbye!")
                    break
                
                if query.lower() == '/help':
                    print("""
🤖 Available Commands:

  /simple <question>  - Use simple retrieval (faster)
  /brief <question>   - Get brief answer
  /bullet <question>  - Get bullet points
  /help               - Show this help
  /quit               - Exit

Examples:
  What is the current USD/PKR rate?
  /brief Why did cement exports rise?
  /bullet Explain the SBP policy decision
                    """)
                    continue
                
                # Parse mode
                use_reasoning = True
                format = "detailed"
                
                if query.startswith('/simple '):
                    query = query[8:].strip()
                    use_reasoning = False
                elif query.startswith('/brief '):
                    query = query[7:].strip()
                    format = "brief"
                elif query.startswith('/bullet '):
                    query = query[8:].strip()
                    format = "bullet"
                
                # Ask question
                answer = self.ask(query, use_reasoning=use_reasoning, format=format)
                self.display_answer(answer)
                
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Fintex Q&A Agent")
    parser.add_argument("--interactive", "-i", action="store_true", help="Run in interactive mode")
    parser.add_argument("--query", "-q", type=str, help="Ask a single question")
    parser.add_argument("--simple", action="store_true", help="Use simple retrieval")
    parser.add_argument("--format", choices=["detailed", "brief", "bullet"], default="detailed", help="Answer format")
    
    args = parser.parse_args()
    
    # Create agent
    agent = QAAgent()
    
    if args.interactive:
        # Interactive mode
        agent.interactive_mode()
    elif args.query:
        # Single question
        answer = agent.ask(
            args.query,
            use_reasoning=not args.simple,
            format=args.format
        )
        agent.display_answer(answer)
    else:
        # Default to interactive
        print("No query specified. Starting interactive mode...\n")
        agent.interactive_mode()


if __name__ == "__main__":
    main()
