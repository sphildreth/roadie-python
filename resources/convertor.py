import os
import json

class Convertor(object):

    config = None

    def __init__(self,folder):
        with open("../settings.json", "r") as rf:
            self.config = json.load(rf)
        for root, dirs, files in os.walk(folder):
            for filename in files:
                    self._convert(os.path.join(root, filename))

    def _convert(self,file):
        exitValue = 1
        fileExtension = os.path.splitext(file)[1].lower()
        outputFilename = os.path.splitext(file)[0]+".mp3"
        if fileExtension == ".flac":
            print("* Converting " + fileExtension + " [" + file + "] to MP3")
            exitValue = os.system("ffmpeg -y -loglevel error -i \"" +  file.replace("/", "\\") + "\" -q:a 0 \"" + outputFilename.replace("/", "\\") + "\"")

        elif fileExtension == ".m4a" or \
           fileExtension == ".ogg":
            print("* Converting " + fileExtension + " [" + file + "] to MP3")
            exitValue = os.system("ffmpeg -y -loglevel error -i \"" +  file.replace("/", "\\") + "\" -acodec libmp3lame -q:a 0 \"" + outputFilename.replace("/", "\\") + "\"")

        if exitValue == 0:
            if 'ROADIE_CONVERTING' in self.config and 'DoDeleteAfter' in self.config['ROADIE_CONVERTING']:
                if self.config['ROADIE_CONVERTING']['DoDeleteAfter'].lower() == "true":
                    try:
                        print("X Deleting [" + file + "]")
                        os.remove(file)
                    except OSError:
                        pass