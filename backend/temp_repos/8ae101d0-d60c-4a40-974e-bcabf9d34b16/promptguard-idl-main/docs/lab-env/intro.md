# Introduction
## Purpose
This document is designed to provide standard specification to ITMX internal to further developing PromptGuard Transaction Risk Score service which will include following topics:  
1. TODO
2. TODO
3. TODO
4. TODO

## Definition
This document will use the following definition:

|      Section            |      Code     |      Meaning     |      Description     |
|---|---|---|---|
|     Institute    |     ITMX    |     National   ITMX    |     National   Interbank Transaction Management and Exchange    |
|  |     MBs    |     Member   Bank(s)    |     ธนาคารสมาชิก   ในโครงการ CFR, สถาบันการเงินภายใต้การกำกับ,   สถาบันการเงิน          |
|  |     Non-bank    |     Non-bank    |     สมาชิกผู้ให้บริการทางการเงินที่ไม่ใช่สถาบันการเงิน, ผู้ให้บริการทางการเงิน (Non-bank)                    |
|  |     FI, FIs    |     Financial   institute(s)    |     ธนาคารสมาชิกและสมาชิกผู้ให้บริการทางการเงินที่ไม่ใช่สถาบันการเงิน   (non-bank) ในโครงการ CFR   ในบางบริบท จะหมายถึงผู้ให้บริการทางการเงินที่ไม่ใช่สถาบันการเงิน (non-bank) เป็นสำคัญ                               |
|     System    |     CFR    |     Central   Fraud Registry    |     Central   Fraud Registry    |
|  |     PP    |     PromptPay    |     ระบบพร้อมเพย์ บริหารจัดการโดย ITMX           |
|     Field    |     M    |     Mandatory    |     The   data element is mandatory and must be provided in the message    |
|  |     C    |     Condition    |     The   data element is optional and may be provided by the message originator with condition    |
|  |     O    |     Optional    |     The   data element is optional and may be provided in the message or do not    |
|  |     N    |     Not   applicable    |     This   field must not be filled in. It is either not required in this context or   should be left blank because providing a value may cause validation issues or   is not permitted by system rules.    |
|  |     X    |     Not   available    |     This   field does not exist in this template/message    |
|  |     P    |     Data   from Police    |     The   data element is required, and system will not detect, not validate by ignore   field value    Due to CCIB system will provide information instead of manual input   information from user    |
|  |     S    |     Data   recorded from system    |     The   data element is required, and system will not detect, not validate by ignore   field value    Due to CFR system will provide information instead of manual input   information from user    |
|  |     MR    |     Match   request or reply    |      Value matches the request value.    |
|  |     N/A    |     Not   available    |     This field does not available for this particular type of message    |
|  |     REQ    |     Request    |     Sender   source will send some data to destination     |
|  |     RES    |     Response    |     Destination   will return the result of request back to the sender source    |
|  |     [1,1]    |     One to   One    |     The   field is required and must be included in the payload. Its value may be   empty, but the field itself must still be provided.    |
|  |     [0..1]    |     Zero to   One    |     Optional   data, limits only one item on the message        In JSON payload, in case of no data, do not send field name and value    |
|  |     [0..0]    |     Zero to   Zero    |     No need   to send data    |
|  |     [0..M]    |     Zero to   Many    |     Optional   data and there is no limit on the message     In JSON payload, in case of no data, do not send field name and value. In   case of this system the maximum limit is 100    |
|  |     [1..M]    |     One to Many    |     This   field must be present in the message and contain at least one value. There is   no upper limit on the number of items. In case of this system the maximum   limit is 100    |