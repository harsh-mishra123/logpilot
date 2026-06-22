import asyncio
import subprocess
from typing import AsyncGenerator, Optional
import logging

logger = logging.getLogger(__name__)

class LogReader:
    """Async log file reader using tail -f"""
    
    def __init__(self, file_path: str, buffer_size: int = 8192):
        self.file_path = file_path
        self.buffer_size = buffer_size
        self.process: Optional[subprocess.Popen] = None
        self.running = False
    
    async def read_lines(self) -> AsyncGenerator[str, None]:
        """Read lines from log file in real-time"""
        self.running = True
        
        try:
            # Use tail -f to follow the file
            self.process = subprocess.Popen(
                ['tail', '-F', self.file_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=self.buffer_size
            )
            
            loop = asyncio.get_event_loop()
            
            while self.running and self.process:
                # Read line asynchronously
                line = await loop.run_in_executor(None, self.process.stdout.readline)
                
                if not line:
                    # End of file or process terminated
                    await asyncio.sleep(0.1)
                    continue
                
                yield line.strip()
                
        except FileNotFoundError:
            logger.error(f"Log file not found: {self.file_path}")
            raise
        except Exception as e:
            logger.error(f"Error reading log file: {e}")
            raise
        finally:
            self.stop()
    
    def stop(self):
        """Stop the tail process"""
        self.running = False
        if self.process:
            self.process.terminate()
            self.process = None
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.stop()
