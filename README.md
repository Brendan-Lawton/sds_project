# SDS Project

## Prerequisites
* Python 3.10

## Setup Instructions
1. Create `.venv` folder
    ```bash
    python3.10 -m venv .venv
    ```

2. Source `.venv` folder
    ```bash
    source .venv/bin/activate
    ```

3. Install `rasa` in the virtual environment
    ```bash
   pip install rasa
    ```
    
4. If you notice that
    ```bash
    rasa run actions
    ```
    is requiring extra install like pytest or bsa, then uninstall rasa and reinstall an earlier version (pip install rasa==3.6.21)
   
6. Add the `asr_server.py` file to the root folder.
7. Add the `web/` folder to the root folder

## Running the Application
Use the start script
```bash
./start_service.sh
```
The application will be accessible at `http://localhost:8080/web/`.

Alternatively, you can run the application directly using the following commands in separate terminal windows:
```bash
rasa run --enable-api --connector rest --cors "*" --port 5005
```
```bash
rasa run actions
```
```bash
python asr_server.py
```
```bash
python -m http.server 8080
```

## Usage
Train the Rasa model:
```bash
rasa train
```

Start the Rasa cli:
```bash
rasa shell
```
