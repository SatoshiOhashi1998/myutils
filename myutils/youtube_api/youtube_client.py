class YouTubeClient:
    def __init__(self, youtube):
        self.youtube = youtube

    def call(self, resource, method, **params):
        func = getattr(getattr(self.youtube, resource)(), method)
        return func(**params).execute()
