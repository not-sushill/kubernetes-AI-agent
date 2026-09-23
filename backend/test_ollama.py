def main():
    from app.ai.ollama_client import OllamaClient
    
    
    client = OllamaClient()
    
    result = client.generate(
        """
    You are a Kubernetes troubleshooting assistant.
    
    A pod is in CrashLoopBackOff.
    
    Give:
    1. likely causes
    2. evidence to inspect
    3. safest remediation approach
    
    Be concise and technical.
    """
    )
    
    print(result)


if __name__ == "__main__":
    main()
