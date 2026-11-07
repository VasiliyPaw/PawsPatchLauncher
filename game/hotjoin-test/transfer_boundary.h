/* FileTransfer.cpp's last-block remainder is zero for exact block multiples.
 * Keep the native block size in that case, on BOTH sender and receiver.
 * These are the displaced native instructions plus TEST/JZ around MOV.
 * Registers, file length/header, block count, ACKs and CRC remain native. */
static const unsigned char hj_transfer_sender_tail[11]={
 0x8b,0xc1,0x99,0xf7,0xfe,0x85,0xd2,0x74,0x02,0x8b,0xf2
};
static const unsigned char hj_transfer_receiver_tail[11]={
 0x8b,0xc6,0x99,0xf7,0xff,0x85,0xd2,0x74,0x02,0x8b,0xfa
};
