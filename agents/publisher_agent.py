from datetime import datetime

class PublisherAgent:
    def execute(self, newsletter_content):
        print("AGENT 5: Publisher - Saving the final newsletter...")
        output_filename = f"newsletter_{datetime.now().strftime('%Y-%m-%d')}.md"
        try:
            with open(output_filename, 'w', encoding='utf-8') as f:
                f.write(newsletter_content)
            print(f"  > Newsletter saved to {output_filename}")
            return output_filename
        except Exception as e:
            print(f"  > FAILED to save newsletter: {e}")
            return None 
