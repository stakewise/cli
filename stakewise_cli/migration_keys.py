from typing import Dict

from .networks import GNOSIS_CHAIN, GOERLI, HARBOUR_GOERLI, HARBOUR_MAINNET, MAINNET
from .typings import MigrationKey

MIGRATION_KEYS: Dict[str, Dict[str, MigrationKey]] = {
    MAINNET: {
        "Cryptomanufaktur": MigrationKey(
            public_key="ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQCt5qgb0lrJ04qM4HY3glvenYLPy+toJ8/wJrrpvTlDFgu1eNP0d7ZNtuyBfZ4kwAs2g6nJqmSTpkjD8sW+y9m8RcVIf0NHu7+kVAAVKvaowyRUiHFMfTwraOWcvw050A5nKMEeOrGOz/rIHQQ9Hu6cAV6P7JyQuoTLUhZXlk2PX06hDW9qxZ9ouFKMFkNoYhVCQ9zyTbTnOjIeVJ2jA/sIk9TadcJ1v7jquxeg6Gwp+/OVHSifDPDlFi3xen3hm/ejP02mBqm8XzT4XpKqKHg568GrSG5pR02kz14Tc7cypnnJoDkSHyOnG6+C2vCcJRfW3dUPEXBY9J4DhRy1of5U2DqqVoPqBG0M+VWjaL2aNr+K8ReBc/2g4WPJmojd1e5/LnqMNhR/r8KLtN8AjBtFXWRfGMWPRJiHN7N9OdmB9KQa5+7yit9tjEOlpJMBNMGnw9wud0yLWiWxNnChdAKO5xiCFgYfXwpQTqxWEZJUNGCyFjsL6ALCKyckfuABpWMVp2VowqQlnKZCNVNr+miDA2CGkxJb+rjx7fr5zCBaCqWCHX1KJSUzwcmkRbB9FJnP/LwsBdAhpF9A/vjMPLcF4JQyuit7LQCnEwJTsGGWMQ9gl5jqi34y18oGgULfrr72NfIZ8wM5pKcntfrPSHo42qGNEslwzV8fSL2EWy7FmQ== CryptoManufaktur",
            validators_count=63,
        ),
        "Finoa": MigrationKey(
            public_key="ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQC1I+q1RvqnH9+vOhcWVhKa0M4/Y16Qa89ICAJUNZrlTzpoCFUoM6gKbouLRVl6ap74WxQWgSuKGoI8XJRNPcgnXtTSnOuj5bSJr5jzaMlVCA6AFn1pi9Al4IhIUWHNTQSI336FLPmnjKvj3W//hPvgg6u35q5pZPCgcwbixHXw0LUhRx6J+Yu9CAY+f0qyJdluYyJCyUjhyRTQ5J75dzAEmUl4szNs51mXRwqQgOf23luOSBMYJU6RUuN2QndoG/v8+XPqTfOKieLiuxgFW/dS2imdVRX6mfUeQoxdtcZCqui9KVmLz1VOxr4WFQDK9KEYXo5qaENh8EiCPaWpvwbDUlrG27VToorC586fCmPvgAKxYmKCNPJgYUY+g77Au2Y/sVlpPv4Fr8KHxRG+KqkctWGuXrkdbZ7xdP0Aj/zhwiHNwA3Fs5UmHJnCeBnc6Ud9earowlaz/V2B51vjNk9JRxnbGQQKeAiGTxf1fZu2gJ/u4DtIF38yzAkFyT/+J58KFhZb8ssUBGJ7/9F4vSb02KEtrp2jK5ELAjW0qtxgfzB/9vFABZjCDAXIP8Wf5HwZJcSgaytLCX8eoU+jQQYwLXgQQGPIMTMUaz0Q5K4M/24sVe+taeIksRI11+l84mUJP+Y5jTBSqFefduVngWR8p0xOd9P2rZPX8QnbVcYINQ== FinoaConsensusServices",
            validators_count=64,
        ),
        "T-Systems": MigrationKey(
            public_key="ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQCt9XnxT51Uqmqr7eo4+K84+A0+ruwRvwT4GxfUhHEhAjNxs06/gPTgGblzHaQTNnxoyw56z/4t/4TSvImrM4BdtgMQnkZgh8ZDxcVgNI6Eo1/fnX/GgZAovWxCQV4vb1HXcM5XSC+B55F/GRnYf/lYALY7xRg1R+ffblv7Q9Uu+jI8eQ/pBUTOZGgSirXGYXBwrb5rPWcylt1b5l5kKWECsiV70vLquMub3CzZhCHz3g/w3x2kNVnw1UT3+v3xh65TCd9YDIHfG9Nfm0R59m2xsPjQ9oidQlTcgNi+YpJtTFTcAo0/kA94HoxDDuVk/mXeJcnj3iWYQ8m3F70HU7visVNBEePA1V3SG8Ao6jelwt7bY0oDEItmh5i/4t4JzCz0AQx5hYF+eq7ZN5TmPbxVGKA4TumMoj+j+Zt7M833hAKes5053x1CJrkVC3v+Nen2HVBPm2M/NOe8Z8ix2ghbsFs84MUN1PXEATl6Byq+7TH6dBD3YPJcYZSWYDGxa7g7n1NOQv7BqkTZv1s9Jz+8B4RmTC+Oc32xDCP4ZogpvwkybP17kNx7tzPAs+XUrHDcAWo7160MQ4256jlhKd86At/Z3Bqfxo9nfBxBEqqR+HkkUpFOEEaK/oi3XqGfUq5e/F8mo+nj2cB26X8pGXb78PxZ1I7V6mzRVjIUZ2L/9Q== T-Systems",
            validators_count=64,
        ),
    },
    HARBOUR_MAINNET: {},
    GOERLI: {},
    HARBOUR_GOERLI: {},
    GNOSIS_CHAIN: {
        "StakeWise Labs": MigrationKey(
            public_key="ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQCVxqFvYSzgUqykDXszuS0ED3IixY5Yl5fDKqK5Me1cEA5Hlj3h4WTAMmfTlEh4LB96yJW9wbSo5cqP6CHz8DV2HmGySlT7aR2FP/PmJcVCumrOKf8Y24rF217zG+mRCyrC9/a4p4HiEaw21ZrApOphMvAd/Zu8PUHUdEIECxxO6VdEWq39woX0F3mKRfq9MrgwkDiMCzBkSG+JN2nscfezGCuXomj2PImHdtIvID9wE89jVjrUqSEhtZhDbvA3ACpDMzRr3YVJ+zOs/oQT3YHwAjBgfMQ5KiKXXFkER/EK2m71p/mmQQHaM0sINO9RLB7Er7k0A8EqTaka4kqWzp3UhtmVaVyknASWv2lcAxQJx4JatViSEfEe5TM77YVlPUtHoF2qvqcHkKQZTRr+gcvIZknBJjR9d2LcnwBez+Yyov3NQfLHEQoQ624q1Q0ASw0YrzO1eGDpgWgxCcN+QCoKZpQG3v/pLQwOkJmjVbExre0/5x8lNI0vq5oxHBupiG2mJE5mrKXopGAyVIfqGyjnY+YAKZShkQ6xQGmHYH9jbV2qp2t29OGBTnTHxa6qJHnIHDz5DuAQCVBEpEMJT72FpW5JAuHIOYnOK6SkIafidFnllMMb4FJAaaVRZs2AY/Ao4H0xT9Ms9LOckYOTyS2XZU50wI9F4AJ4c6sLauHtZw== StakeWise Labs",
            validators_count=4971,
        ),
        "CryptoManufaktur": MigrationKey(
            public_key="ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQCt5qgb0lrJ04qM4HY3glvenYLPy+toJ8/wJrrpvTlDFgu1eNP0d7ZNtuyBfZ4kwAs2g6nJqmSTpkjD8sW+y9m8RcVIf0NHu7+kVAAVKvaowyRUiHFMfTwraOWcvw050A5nKMEeOrGOz/rIHQQ9Hu6cAV6P7JyQuoTLUhZXlk2PX06hDW9qxZ9ouFKMFkNoYhVCQ9zyTbTnOjIeVJ2jA/sIk9TadcJ1v7jquxeg6Gwp+/OVHSifDPDlFi3xen3hm/ejP02mBqm8XzT4XpKqKHg568GrSG5pR02kz14Tc7cypnnJoDkSHyOnG6+C2vCcJRfW3dUPEXBY9J4DhRy1of5U2DqqVoPqBG0M+VWjaL2aNr+K8ReBc/2g4WPJmojd1e5/LnqMNhR/r8KLtN8AjBtFXWRfGMWPRJiHN7N9OdmB9KQa5+7yit9tjEOlpJMBNMGnw9wud0yLWiWxNnChdAKO5xiCFgYfXwpQTqxWEZJUNGCyFjsL6ALCKyckfuABpWMVp2VowqQlnKZCNVNr+miDA2CGkxJb+rjx7fr5zCBaCqWCHX1KJSUzwcmkRbB9FJnP/LwsBdAhpF9A/vjMPLcF4JQyuit7LQCnEwJTsGGWMQ9gl5jqi34y18oGgULfrr72NfIZ8wM5pKcntfrPSHo42qGNEslwzV8fSL2EWy7FmQ== CryptoManufaktur",
            validators_count=4971,
        ),
    },
}
