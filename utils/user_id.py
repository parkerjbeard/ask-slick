class UserIDManager:
    @staticmethod
    def normalize_user_id(user_id: str, platform: str = 'slack') -> str:
        """
        Normalize user IDs across different platforms
        
        Args:
            user_id (str): The raw user ID
            platform (str): The platform prefix ('slack', 'discord', 'web', etc.)
            
        Returns:
            str: Normalized user ID with platform prefix
        """
        if not user_id:
            raise ValueError("User ID cannot be empty")
            
        # Remove any existing platform prefix
        for prefix in ['slack_', 'discord_', 'web_']:
            if user_id.startswith(prefix):
                user_id = user_id[len(prefix):]
                break
                
        return f"{platform}_{user_id}"

    @staticmethod
    def get_platform(user_id: str) -> str:
        """Extract platform from normalized user ID"""
        if '_' not in user_id:
            return 'slack'  # Default platform
        return user_id.split('_')[0]