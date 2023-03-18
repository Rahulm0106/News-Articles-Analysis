## VM SSH Setup

* Create an ssh key in your local system in the `.ssh` folder - [Guide](https://cloud.google.com/compute/docs/connect/create-ssh-keys#linux-and-macos)

* Enable Commute Engine API

* Copy the public key from (`.pub`) file

* Open metadata under compute engine and add public key copied from (`.pub`) file in SSH KEYS section

* Create a config file in your `.ssh` folder

  ```bash
  touch ~/.ssh/config
  ```

* Copy the following snippet and replace with External IP of Airflow VM. Username and path to the ssh private key

    ```bash
    Host newsarticles-airflow
        HostName <External IP Address>
        User <username>
        IdentityFile <path/to/home/.ssh/gcp>
    ```

* Once you are setup, you can simply SSH into the server using the below command in terminal. Do not forget to change the IP address of VM restarts.
    ```bash
    ssh streamify-airflow
    ```

* You will have to forward ports from your VM to your local machine for you to be able to see Airflow UI. Check how to do that [here](https://youtu.be/ae-CV2KfoN0?t=1074)

