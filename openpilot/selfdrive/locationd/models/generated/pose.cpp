#include "pose.h"

namespace {
#define DIM 18
#define EDIM 18
#define MEDIM 18
typedef void (*Hfun)(double *, double *, double *);
const static double MAHA_THRESH_4 = 7.814727903251177;
const static double MAHA_THRESH_10 = 7.814727903251177;
const static double MAHA_THRESH_13 = 7.814727903251177;
const static double MAHA_THRESH_14 = 7.814727903251177;

/******************************************************************************
 *                      Code generated with SymPy 1.14.0                      *
 *                                                                            *
 *              See http://www.sympy.org/ for more information.               *
 *                                                                            *
 *                         This file is part of 'ekf'                         *
 ******************************************************************************/
void err_fun(double *nom_x, double *delta_x, double *out_5818094549552656547) {
   out_5818094549552656547[0] = delta_x[0] + nom_x[0];
   out_5818094549552656547[1] = delta_x[1] + nom_x[1];
   out_5818094549552656547[2] = delta_x[2] + nom_x[2];
   out_5818094549552656547[3] = delta_x[3] + nom_x[3];
   out_5818094549552656547[4] = delta_x[4] + nom_x[4];
   out_5818094549552656547[5] = delta_x[5] + nom_x[5];
   out_5818094549552656547[6] = delta_x[6] + nom_x[6];
   out_5818094549552656547[7] = delta_x[7] + nom_x[7];
   out_5818094549552656547[8] = delta_x[8] + nom_x[8];
   out_5818094549552656547[9] = delta_x[9] + nom_x[9];
   out_5818094549552656547[10] = delta_x[10] + nom_x[10];
   out_5818094549552656547[11] = delta_x[11] + nom_x[11];
   out_5818094549552656547[12] = delta_x[12] + nom_x[12];
   out_5818094549552656547[13] = delta_x[13] + nom_x[13];
   out_5818094549552656547[14] = delta_x[14] + nom_x[14];
   out_5818094549552656547[15] = delta_x[15] + nom_x[15];
   out_5818094549552656547[16] = delta_x[16] + nom_x[16];
   out_5818094549552656547[17] = delta_x[17] + nom_x[17];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_3606049234714008263) {
   out_3606049234714008263[0] = -nom_x[0] + true_x[0];
   out_3606049234714008263[1] = -nom_x[1] + true_x[1];
   out_3606049234714008263[2] = -nom_x[2] + true_x[2];
   out_3606049234714008263[3] = -nom_x[3] + true_x[3];
   out_3606049234714008263[4] = -nom_x[4] + true_x[4];
   out_3606049234714008263[5] = -nom_x[5] + true_x[5];
   out_3606049234714008263[6] = -nom_x[6] + true_x[6];
   out_3606049234714008263[7] = -nom_x[7] + true_x[7];
   out_3606049234714008263[8] = -nom_x[8] + true_x[8];
   out_3606049234714008263[9] = -nom_x[9] + true_x[9];
   out_3606049234714008263[10] = -nom_x[10] + true_x[10];
   out_3606049234714008263[11] = -nom_x[11] + true_x[11];
   out_3606049234714008263[12] = -nom_x[12] + true_x[12];
   out_3606049234714008263[13] = -nom_x[13] + true_x[13];
   out_3606049234714008263[14] = -nom_x[14] + true_x[14];
   out_3606049234714008263[15] = -nom_x[15] + true_x[15];
   out_3606049234714008263[16] = -nom_x[16] + true_x[16];
   out_3606049234714008263[17] = -nom_x[17] + true_x[17];
}
void H_mod_fun(double *state, double *out_1632125326007639956) {
   out_1632125326007639956[0] = 1.0;
   out_1632125326007639956[1] = 0.0;
   out_1632125326007639956[2] = 0.0;
   out_1632125326007639956[3] = 0.0;
   out_1632125326007639956[4] = 0.0;
   out_1632125326007639956[5] = 0.0;
   out_1632125326007639956[6] = 0.0;
   out_1632125326007639956[7] = 0.0;
   out_1632125326007639956[8] = 0.0;
   out_1632125326007639956[9] = 0.0;
   out_1632125326007639956[10] = 0.0;
   out_1632125326007639956[11] = 0.0;
   out_1632125326007639956[12] = 0.0;
   out_1632125326007639956[13] = 0.0;
   out_1632125326007639956[14] = 0.0;
   out_1632125326007639956[15] = 0.0;
   out_1632125326007639956[16] = 0.0;
   out_1632125326007639956[17] = 0.0;
   out_1632125326007639956[18] = 0.0;
   out_1632125326007639956[19] = 1.0;
   out_1632125326007639956[20] = 0.0;
   out_1632125326007639956[21] = 0.0;
   out_1632125326007639956[22] = 0.0;
   out_1632125326007639956[23] = 0.0;
   out_1632125326007639956[24] = 0.0;
   out_1632125326007639956[25] = 0.0;
   out_1632125326007639956[26] = 0.0;
   out_1632125326007639956[27] = 0.0;
   out_1632125326007639956[28] = 0.0;
   out_1632125326007639956[29] = 0.0;
   out_1632125326007639956[30] = 0.0;
   out_1632125326007639956[31] = 0.0;
   out_1632125326007639956[32] = 0.0;
   out_1632125326007639956[33] = 0.0;
   out_1632125326007639956[34] = 0.0;
   out_1632125326007639956[35] = 0.0;
   out_1632125326007639956[36] = 0.0;
   out_1632125326007639956[37] = 0.0;
   out_1632125326007639956[38] = 1.0;
   out_1632125326007639956[39] = 0.0;
   out_1632125326007639956[40] = 0.0;
   out_1632125326007639956[41] = 0.0;
   out_1632125326007639956[42] = 0.0;
   out_1632125326007639956[43] = 0.0;
   out_1632125326007639956[44] = 0.0;
   out_1632125326007639956[45] = 0.0;
   out_1632125326007639956[46] = 0.0;
   out_1632125326007639956[47] = 0.0;
   out_1632125326007639956[48] = 0.0;
   out_1632125326007639956[49] = 0.0;
   out_1632125326007639956[50] = 0.0;
   out_1632125326007639956[51] = 0.0;
   out_1632125326007639956[52] = 0.0;
   out_1632125326007639956[53] = 0.0;
   out_1632125326007639956[54] = 0.0;
   out_1632125326007639956[55] = 0.0;
   out_1632125326007639956[56] = 0.0;
   out_1632125326007639956[57] = 1.0;
   out_1632125326007639956[58] = 0.0;
   out_1632125326007639956[59] = 0.0;
   out_1632125326007639956[60] = 0.0;
   out_1632125326007639956[61] = 0.0;
   out_1632125326007639956[62] = 0.0;
   out_1632125326007639956[63] = 0.0;
   out_1632125326007639956[64] = 0.0;
   out_1632125326007639956[65] = 0.0;
   out_1632125326007639956[66] = 0.0;
   out_1632125326007639956[67] = 0.0;
   out_1632125326007639956[68] = 0.0;
   out_1632125326007639956[69] = 0.0;
   out_1632125326007639956[70] = 0.0;
   out_1632125326007639956[71] = 0.0;
   out_1632125326007639956[72] = 0.0;
   out_1632125326007639956[73] = 0.0;
   out_1632125326007639956[74] = 0.0;
   out_1632125326007639956[75] = 0.0;
   out_1632125326007639956[76] = 1.0;
   out_1632125326007639956[77] = 0.0;
   out_1632125326007639956[78] = 0.0;
   out_1632125326007639956[79] = 0.0;
   out_1632125326007639956[80] = 0.0;
   out_1632125326007639956[81] = 0.0;
   out_1632125326007639956[82] = 0.0;
   out_1632125326007639956[83] = 0.0;
   out_1632125326007639956[84] = 0.0;
   out_1632125326007639956[85] = 0.0;
   out_1632125326007639956[86] = 0.0;
   out_1632125326007639956[87] = 0.0;
   out_1632125326007639956[88] = 0.0;
   out_1632125326007639956[89] = 0.0;
   out_1632125326007639956[90] = 0.0;
   out_1632125326007639956[91] = 0.0;
   out_1632125326007639956[92] = 0.0;
   out_1632125326007639956[93] = 0.0;
   out_1632125326007639956[94] = 0.0;
   out_1632125326007639956[95] = 1.0;
   out_1632125326007639956[96] = 0.0;
   out_1632125326007639956[97] = 0.0;
   out_1632125326007639956[98] = 0.0;
   out_1632125326007639956[99] = 0.0;
   out_1632125326007639956[100] = 0.0;
   out_1632125326007639956[101] = 0.0;
   out_1632125326007639956[102] = 0.0;
   out_1632125326007639956[103] = 0.0;
   out_1632125326007639956[104] = 0.0;
   out_1632125326007639956[105] = 0.0;
   out_1632125326007639956[106] = 0.0;
   out_1632125326007639956[107] = 0.0;
   out_1632125326007639956[108] = 0.0;
   out_1632125326007639956[109] = 0.0;
   out_1632125326007639956[110] = 0.0;
   out_1632125326007639956[111] = 0.0;
   out_1632125326007639956[112] = 0.0;
   out_1632125326007639956[113] = 0.0;
   out_1632125326007639956[114] = 1.0;
   out_1632125326007639956[115] = 0.0;
   out_1632125326007639956[116] = 0.0;
   out_1632125326007639956[117] = 0.0;
   out_1632125326007639956[118] = 0.0;
   out_1632125326007639956[119] = 0.0;
   out_1632125326007639956[120] = 0.0;
   out_1632125326007639956[121] = 0.0;
   out_1632125326007639956[122] = 0.0;
   out_1632125326007639956[123] = 0.0;
   out_1632125326007639956[124] = 0.0;
   out_1632125326007639956[125] = 0.0;
   out_1632125326007639956[126] = 0.0;
   out_1632125326007639956[127] = 0.0;
   out_1632125326007639956[128] = 0.0;
   out_1632125326007639956[129] = 0.0;
   out_1632125326007639956[130] = 0.0;
   out_1632125326007639956[131] = 0.0;
   out_1632125326007639956[132] = 0.0;
   out_1632125326007639956[133] = 1.0;
   out_1632125326007639956[134] = 0.0;
   out_1632125326007639956[135] = 0.0;
   out_1632125326007639956[136] = 0.0;
   out_1632125326007639956[137] = 0.0;
   out_1632125326007639956[138] = 0.0;
   out_1632125326007639956[139] = 0.0;
   out_1632125326007639956[140] = 0.0;
   out_1632125326007639956[141] = 0.0;
   out_1632125326007639956[142] = 0.0;
   out_1632125326007639956[143] = 0.0;
   out_1632125326007639956[144] = 0.0;
   out_1632125326007639956[145] = 0.0;
   out_1632125326007639956[146] = 0.0;
   out_1632125326007639956[147] = 0.0;
   out_1632125326007639956[148] = 0.0;
   out_1632125326007639956[149] = 0.0;
   out_1632125326007639956[150] = 0.0;
   out_1632125326007639956[151] = 0.0;
   out_1632125326007639956[152] = 1.0;
   out_1632125326007639956[153] = 0.0;
   out_1632125326007639956[154] = 0.0;
   out_1632125326007639956[155] = 0.0;
   out_1632125326007639956[156] = 0.0;
   out_1632125326007639956[157] = 0.0;
   out_1632125326007639956[158] = 0.0;
   out_1632125326007639956[159] = 0.0;
   out_1632125326007639956[160] = 0.0;
   out_1632125326007639956[161] = 0.0;
   out_1632125326007639956[162] = 0.0;
   out_1632125326007639956[163] = 0.0;
   out_1632125326007639956[164] = 0.0;
   out_1632125326007639956[165] = 0.0;
   out_1632125326007639956[166] = 0.0;
   out_1632125326007639956[167] = 0.0;
   out_1632125326007639956[168] = 0.0;
   out_1632125326007639956[169] = 0.0;
   out_1632125326007639956[170] = 0.0;
   out_1632125326007639956[171] = 1.0;
   out_1632125326007639956[172] = 0.0;
   out_1632125326007639956[173] = 0.0;
   out_1632125326007639956[174] = 0.0;
   out_1632125326007639956[175] = 0.0;
   out_1632125326007639956[176] = 0.0;
   out_1632125326007639956[177] = 0.0;
   out_1632125326007639956[178] = 0.0;
   out_1632125326007639956[179] = 0.0;
   out_1632125326007639956[180] = 0.0;
   out_1632125326007639956[181] = 0.0;
   out_1632125326007639956[182] = 0.0;
   out_1632125326007639956[183] = 0.0;
   out_1632125326007639956[184] = 0.0;
   out_1632125326007639956[185] = 0.0;
   out_1632125326007639956[186] = 0.0;
   out_1632125326007639956[187] = 0.0;
   out_1632125326007639956[188] = 0.0;
   out_1632125326007639956[189] = 0.0;
   out_1632125326007639956[190] = 1.0;
   out_1632125326007639956[191] = 0.0;
   out_1632125326007639956[192] = 0.0;
   out_1632125326007639956[193] = 0.0;
   out_1632125326007639956[194] = 0.0;
   out_1632125326007639956[195] = 0.0;
   out_1632125326007639956[196] = 0.0;
   out_1632125326007639956[197] = 0.0;
   out_1632125326007639956[198] = 0.0;
   out_1632125326007639956[199] = 0.0;
   out_1632125326007639956[200] = 0.0;
   out_1632125326007639956[201] = 0.0;
   out_1632125326007639956[202] = 0.0;
   out_1632125326007639956[203] = 0.0;
   out_1632125326007639956[204] = 0.0;
   out_1632125326007639956[205] = 0.0;
   out_1632125326007639956[206] = 0.0;
   out_1632125326007639956[207] = 0.0;
   out_1632125326007639956[208] = 0.0;
   out_1632125326007639956[209] = 1.0;
   out_1632125326007639956[210] = 0.0;
   out_1632125326007639956[211] = 0.0;
   out_1632125326007639956[212] = 0.0;
   out_1632125326007639956[213] = 0.0;
   out_1632125326007639956[214] = 0.0;
   out_1632125326007639956[215] = 0.0;
   out_1632125326007639956[216] = 0.0;
   out_1632125326007639956[217] = 0.0;
   out_1632125326007639956[218] = 0.0;
   out_1632125326007639956[219] = 0.0;
   out_1632125326007639956[220] = 0.0;
   out_1632125326007639956[221] = 0.0;
   out_1632125326007639956[222] = 0.0;
   out_1632125326007639956[223] = 0.0;
   out_1632125326007639956[224] = 0.0;
   out_1632125326007639956[225] = 0.0;
   out_1632125326007639956[226] = 0.0;
   out_1632125326007639956[227] = 0.0;
   out_1632125326007639956[228] = 1.0;
   out_1632125326007639956[229] = 0.0;
   out_1632125326007639956[230] = 0.0;
   out_1632125326007639956[231] = 0.0;
   out_1632125326007639956[232] = 0.0;
   out_1632125326007639956[233] = 0.0;
   out_1632125326007639956[234] = 0.0;
   out_1632125326007639956[235] = 0.0;
   out_1632125326007639956[236] = 0.0;
   out_1632125326007639956[237] = 0.0;
   out_1632125326007639956[238] = 0.0;
   out_1632125326007639956[239] = 0.0;
   out_1632125326007639956[240] = 0.0;
   out_1632125326007639956[241] = 0.0;
   out_1632125326007639956[242] = 0.0;
   out_1632125326007639956[243] = 0.0;
   out_1632125326007639956[244] = 0.0;
   out_1632125326007639956[245] = 0.0;
   out_1632125326007639956[246] = 0.0;
   out_1632125326007639956[247] = 1.0;
   out_1632125326007639956[248] = 0.0;
   out_1632125326007639956[249] = 0.0;
   out_1632125326007639956[250] = 0.0;
   out_1632125326007639956[251] = 0.0;
   out_1632125326007639956[252] = 0.0;
   out_1632125326007639956[253] = 0.0;
   out_1632125326007639956[254] = 0.0;
   out_1632125326007639956[255] = 0.0;
   out_1632125326007639956[256] = 0.0;
   out_1632125326007639956[257] = 0.0;
   out_1632125326007639956[258] = 0.0;
   out_1632125326007639956[259] = 0.0;
   out_1632125326007639956[260] = 0.0;
   out_1632125326007639956[261] = 0.0;
   out_1632125326007639956[262] = 0.0;
   out_1632125326007639956[263] = 0.0;
   out_1632125326007639956[264] = 0.0;
   out_1632125326007639956[265] = 0.0;
   out_1632125326007639956[266] = 1.0;
   out_1632125326007639956[267] = 0.0;
   out_1632125326007639956[268] = 0.0;
   out_1632125326007639956[269] = 0.0;
   out_1632125326007639956[270] = 0.0;
   out_1632125326007639956[271] = 0.0;
   out_1632125326007639956[272] = 0.0;
   out_1632125326007639956[273] = 0.0;
   out_1632125326007639956[274] = 0.0;
   out_1632125326007639956[275] = 0.0;
   out_1632125326007639956[276] = 0.0;
   out_1632125326007639956[277] = 0.0;
   out_1632125326007639956[278] = 0.0;
   out_1632125326007639956[279] = 0.0;
   out_1632125326007639956[280] = 0.0;
   out_1632125326007639956[281] = 0.0;
   out_1632125326007639956[282] = 0.0;
   out_1632125326007639956[283] = 0.0;
   out_1632125326007639956[284] = 0.0;
   out_1632125326007639956[285] = 1.0;
   out_1632125326007639956[286] = 0.0;
   out_1632125326007639956[287] = 0.0;
   out_1632125326007639956[288] = 0.0;
   out_1632125326007639956[289] = 0.0;
   out_1632125326007639956[290] = 0.0;
   out_1632125326007639956[291] = 0.0;
   out_1632125326007639956[292] = 0.0;
   out_1632125326007639956[293] = 0.0;
   out_1632125326007639956[294] = 0.0;
   out_1632125326007639956[295] = 0.0;
   out_1632125326007639956[296] = 0.0;
   out_1632125326007639956[297] = 0.0;
   out_1632125326007639956[298] = 0.0;
   out_1632125326007639956[299] = 0.0;
   out_1632125326007639956[300] = 0.0;
   out_1632125326007639956[301] = 0.0;
   out_1632125326007639956[302] = 0.0;
   out_1632125326007639956[303] = 0.0;
   out_1632125326007639956[304] = 1.0;
   out_1632125326007639956[305] = 0.0;
   out_1632125326007639956[306] = 0.0;
   out_1632125326007639956[307] = 0.0;
   out_1632125326007639956[308] = 0.0;
   out_1632125326007639956[309] = 0.0;
   out_1632125326007639956[310] = 0.0;
   out_1632125326007639956[311] = 0.0;
   out_1632125326007639956[312] = 0.0;
   out_1632125326007639956[313] = 0.0;
   out_1632125326007639956[314] = 0.0;
   out_1632125326007639956[315] = 0.0;
   out_1632125326007639956[316] = 0.0;
   out_1632125326007639956[317] = 0.0;
   out_1632125326007639956[318] = 0.0;
   out_1632125326007639956[319] = 0.0;
   out_1632125326007639956[320] = 0.0;
   out_1632125326007639956[321] = 0.0;
   out_1632125326007639956[322] = 0.0;
   out_1632125326007639956[323] = 1.0;
}
void f_fun(double *state, double dt, double *out_6251314416692735066) {
   out_6251314416692735066[0] = atan2((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), -(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]));
   out_6251314416692735066[1] = asin(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]));
   out_6251314416692735066[2] = atan2(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), -(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]));
   out_6251314416692735066[3] = dt*state[12] + state[3];
   out_6251314416692735066[4] = dt*state[13] + state[4];
   out_6251314416692735066[5] = dt*state[14] + state[5];
   out_6251314416692735066[6] = state[6];
   out_6251314416692735066[7] = state[7];
   out_6251314416692735066[8] = state[8];
   out_6251314416692735066[9] = state[9];
   out_6251314416692735066[10] = state[10];
   out_6251314416692735066[11] = state[11];
   out_6251314416692735066[12] = state[12];
   out_6251314416692735066[13] = state[13];
   out_6251314416692735066[14] = state[14];
   out_6251314416692735066[15] = state[15];
   out_6251314416692735066[16] = state[16];
   out_6251314416692735066[17] = state[17];
}
void F_fun(double *state, double dt, double *out_4702066556653843398) {
   out_4702066556653843398[0] = ((-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*cos(state[0])*cos(state[1]) - sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*cos(state[0])*cos(state[1]) - sin(dt*state[6])*sin(state[0])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_4702066556653843398[1] = ((-sin(dt*state[6])*sin(dt*state[8]) - sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*cos(state[1]) - (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*sin(state[1]) - sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(state[0]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*sin(state[1]) + (-sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) + sin(dt*state[8])*cos(dt*state[6]))*cos(state[1]) - sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(state[0]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_4702066556653843398[2] = 0;
   out_4702066556653843398[3] = 0;
   out_4702066556653843398[4] = 0;
   out_4702066556653843398[5] = 0;
   out_4702066556653843398[6] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(dt*cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) - dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_4702066556653843398[7] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*sin(dt*state[7])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[6])*sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) - dt*sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[7])*cos(dt*state[6])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[8])*sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]) - dt*sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_4702066556653843398[8] = ((dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((dt*sin(dt*state[6])*sin(dt*state[8]) + dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_4702066556653843398[9] = 0;
   out_4702066556653843398[10] = 0;
   out_4702066556653843398[11] = 0;
   out_4702066556653843398[12] = 0;
   out_4702066556653843398[13] = 0;
   out_4702066556653843398[14] = 0;
   out_4702066556653843398[15] = 0;
   out_4702066556653843398[16] = 0;
   out_4702066556653843398[17] = 0;
   out_4702066556653843398[18] = (-sin(dt*state[7])*sin(state[0])*cos(state[1]) - sin(dt*state[8])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_4702066556653843398[19] = (-sin(dt*state[7])*sin(state[1])*cos(state[0]) + sin(dt*state[8])*sin(state[0])*sin(state[1])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_4702066556653843398[20] = 0;
   out_4702066556653843398[21] = 0;
   out_4702066556653843398[22] = 0;
   out_4702066556653843398[23] = 0;
   out_4702066556653843398[24] = 0;
   out_4702066556653843398[25] = (dt*sin(dt*state[7])*sin(dt*state[8])*sin(state[0])*cos(state[1]) - dt*sin(dt*state[7])*sin(state[1])*cos(dt*state[8]) + dt*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_4702066556653843398[26] = (-dt*sin(dt*state[8])*sin(state[1])*cos(dt*state[7]) - dt*sin(state[0])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_4702066556653843398[27] = 0;
   out_4702066556653843398[28] = 0;
   out_4702066556653843398[29] = 0;
   out_4702066556653843398[30] = 0;
   out_4702066556653843398[31] = 0;
   out_4702066556653843398[32] = 0;
   out_4702066556653843398[33] = 0;
   out_4702066556653843398[34] = 0;
   out_4702066556653843398[35] = 0;
   out_4702066556653843398[36] = ((sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_4702066556653843398[37] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-sin(dt*state[7])*sin(state[2])*cos(state[0])*cos(state[1]) + sin(dt*state[8])*sin(state[0])*sin(state[2])*cos(dt*state[7])*cos(state[1]) - sin(state[1])*sin(state[2])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(-sin(dt*state[7])*cos(state[0])*cos(state[1])*cos(state[2]) + sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1])*cos(state[2]) - sin(state[1])*cos(dt*state[7])*cos(dt*state[8])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_4702066556653843398[38] = ((-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (-sin(state[0])*sin(state[1])*sin(state[2]) - cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_4702066556653843398[39] = 0;
   out_4702066556653843398[40] = 0;
   out_4702066556653843398[41] = 0;
   out_4702066556653843398[42] = 0;
   out_4702066556653843398[43] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(dt*(sin(state[0])*cos(state[2]) - sin(state[1])*sin(state[2])*cos(state[0]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*sin(state[2])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(dt*(-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_4702066556653843398[44] = (dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*sin(state[2])*cos(dt*state[7])*cos(state[1]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + (dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[7])*cos(state[1])*cos(state[2]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_4702066556653843398[45] = 0;
   out_4702066556653843398[46] = 0;
   out_4702066556653843398[47] = 0;
   out_4702066556653843398[48] = 0;
   out_4702066556653843398[49] = 0;
   out_4702066556653843398[50] = 0;
   out_4702066556653843398[51] = 0;
   out_4702066556653843398[52] = 0;
   out_4702066556653843398[53] = 0;
   out_4702066556653843398[54] = 0;
   out_4702066556653843398[55] = 0;
   out_4702066556653843398[56] = 0;
   out_4702066556653843398[57] = 1;
   out_4702066556653843398[58] = 0;
   out_4702066556653843398[59] = 0;
   out_4702066556653843398[60] = 0;
   out_4702066556653843398[61] = 0;
   out_4702066556653843398[62] = 0;
   out_4702066556653843398[63] = 0;
   out_4702066556653843398[64] = 0;
   out_4702066556653843398[65] = 0;
   out_4702066556653843398[66] = dt;
   out_4702066556653843398[67] = 0;
   out_4702066556653843398[68] = 0;
   out_4702066556653843398[69] = 0;
   out_4702066556653843398[70] = 0;
   out_4702066556653843398[71] = 0;
   out_4702066556653843398[72] = 0;
   out_4702066556653843398[73] = 0;
   out_4702066556653843398[74] = 0;
   out_4702066556653843398[75] = 0;
   out_4702066556653843398[76] = 1;
   out_4702066556653843398[77] = 0;
   out_4702066556653843398[78] = 0;
   out_4702066556653843398[79] = 0;
   out_4702066556653843398[80] = 0;
   out_4702066556653843398[81] = 0;
   out_4702066556653843398[82] = 0;
   out_4702066556653843398[83] = 0;
   out_4702066556653843398[84] = 0;
   out_4702066556653843398[85] = dt;
   out_4702066556653843398[86] = 0;
   out_4702066556653843398[87] = 0;
   out_4702066556653843398[88] = 0;
   out_4702066556653843398[89] = 0;
   out_4702066556653843398[90] = 0;
   out_4702066556653843398[91] = 0;
   out_4702066556653843398[92] = 0;
   out_4702066556653843398[93] = 0;
   out_4702066556653843398[94] = 0;
   out_4702066556653843398[95] = 1;
   out_4702066556653843398[96] = 0;
   out_4702066556653843398[97] = 0;
   out_4702066556653843398[98] = 0;
   out_4702066556653843398[99] = 0;
   out_4702066556653843398[100] = 0;
   out_4702066556653843398[101] = 0;
   out_4702066556653843398[102] = 0;
   out_4702066556653843398[103] = 0;
   out_4702066556653843398[104] = dt;
   out_4702066556653843398[105] = 0;
   out_4702066556653843398[106] = 0;
   out_4702066556653843398[107] = 0;
   out_4702066556653843398[108] = 0;
   out_4702066556653843398[109] = 0;
   out_4702066556653843398[110] = 0;
   out_4702066556653843398[111] = 0;
   out_4702066556653843398[112] = 0;
   out_4702066556653843398[113] = 0;
   out_4702066556653843398[114] = 1;
   out_4702066556653843398[115] = 0;
   out_4702066556653843398[116] = 0;
   out_4702066556653843398[117] = 0;
   out_4702066556653843398[118] = 0;
   out_4702066556653843398[119] = 0;
   out_4702066556653843398[120] = 0;
   out_4702066556653843398[121] = 0;
   out_4702066556653843398[122] = 0;
   out_4702066556653843398[123] = 0;
   out_4702066556653843398[124] = 0;
   out_4702066556653843398[125] = 0;
   out_4702066556653843398[126] = 0;
   out_4702066556653843398[127] = 0;
   out_4702066556653843398[128] = 0;
   out_4702066556653843398[129] = 0;
   out_4702066556653843398[130] = 0;
   out_4702066556653843398[131] = 0;
   out_4702066556653843398[132] = 0;
   out_4702066556653843398[133] = 1;
   out_4702066556653843398[134] = 0;
   out_4702066556653843398[135] = 0;
   out_4702066556653843398[136] = 0;
   out_4702066556653843398[137] = 0;
   out_4702066556653843398[138] = 0;
   out_4702066556653843398[139] = 0;
   out_4702066556653843398[140] = 0;
   out_4702066556653843398[141] = 0;
   out_4702066556653843398[142] = 0;
   out_4702066556653843398[143] = 0;
   out_4702066556653843398[144] = 0;
   out_4702066556653843398[145] = 0;
   out_4702066556653843398[146] = 0;
   out_4702066556653843398[147] = 0;
   out_4702066556653843398[148] = 0;
   out_4702066556653843398[149] = 0;
   out_4702066556653843398[150] = 0;
   out_4702066556653843398[151] = 0;
   out_4702066556653843398[152] = 1;
   out_4702066556653843398[153] = 0;
   out_4702066556653843398[154] = 0;
   out_4702066556653843398[155] = 0;
   out_4702066556653843398[156] = 0;
   out_4702066556653843398[157] = 0;
   out_4702066556653843398[158] = 0;
   out_4702066556653843398[159] = 0;
   out_4702066556653843398[160] = 0;
   out_4702066556653843398[161] = 0;
   out_4702066556653843398[162] = 0;
   out_4702066556653843398[163] = 0;
   out_4702066556653843398[164] = 0;
   out_4702066556653843398[165] = 0;
   out_4702066556653843398[166] = 0;
   out_4702066556653843398[167] = 0;
   out_4702066556653843398[168] = 0;
   out_4702066556653843398[169] = 0;
   out_4702066556653843398[170] = 0;
   out_4702066556653843398[171] = 1;
   out_4702066556653843398[172] = 0;
   out_4702066556653843398[173] = 0;
   out_4702066556653843398[174] = 0;
   out_4702066556653843398[175] = 0;
   out_4702066556653843398[176] = 0;
   out_4702066556653843398[177] = 0;
   out_4702066556653843398[178] = 0;
   out_4702066556653843398[179] = 0;
   out_4702066556653843398[180] = 0;
   out_4702066556653843398[181] = 0;
   out_4702066556653843398[182] = 0;
   out_4702066556653843398[183] = 0;
   out_4702066556653843398[184] = 0;
   out_4702066556653843398[185] = 0;
   out_4702066556653843398[186] = 0;
   out_4702066556653843398[187] = 0;
   out_4702066556653843398[188] = 0;
   out_4702066556653843398[189] = 0;
   out_4702066556653843398[190] = 1;
   out_4702066556653843398[191] = 0;
   out_4702066556653843398[192] = 0;
   out_4702066556653843398[193] = 0;
   out_4702066556653843398[194] = 0;
   out_4702066556653843398[195] = 0;
   out_4702066556653843398[196] = 0;
   out_4702066556653843398[197] = 0;
   out_4702066556653843398[198] = 0;
   out_4702066556653843398[199] = 0;
   out_4702066556653843398[200] = 0;
   out_4702066556653843398[201] = 0;
   out_4702066556653843398[202] = 0;
   out_4702066556653843398[203] = 0;
   out_4702066556653843398[204] = 0;
   out_4702066556653843398[205] = 0;
   out_4702066556653843398[206] = 0;
   out_4702066556653843398[207] = 0;
   out_4702066556653843398[208] = 0;
   out_4702066556653843398[209] = 1;
   out_4702066556653843398[210] = 0;
   out_4702066556653843398[211] = 0;
   out_4702066556653843398[212] = 0;
   out_4702066556653843398[213] = 0;
   out_4702066556653843398[214] = 0;
   out_4702066556653843398[215] = 0;
   out_4702066556653843398[216] = 0;
   out_4702066556653843398[217] = 0;
   out_4702066556653843398[218] = 0;
   out_4702066556653843398[219] = 0;
   out_4702066556653843398[220] = 0;
   out_4702066556653843398[221] = 0;
   out_4702066556653843398[222] = 0;
   out_4702066556653843398[223] = 0;
   out_4702066556653843398[224] = 0;
   out_4702066556653843398[225] = 0;
   out_4702066556653843398[226] = 0;
   out_4702066556653843398[227] = 0;
   out_4702066556653843398[228] = 1;
   out_4702066556653843398[229] = 0;
   out_4702066556653843398[230] = 0;
   out_4702066556653843398[231] = 0;
   out_4702066556653843398[232] = 0;
   out_4702066556653843398[233] = 0;
   out_4702066556653843398[234] = 0;
   out_4702066556653843398[235] = 0;
   out_4702066556653843398[236] = 0;
   out_4702066556653843398[237] = 0;
   out_4702066556653843398[238] = 0;
   out_4702066556653843398[239] = 0;
   out_4702066556653843398[240] = 0;
   out_4702066556653843398[241] = 0;
   out_4702066556653843398[242] = 0;
   out_4702066556653843398[243] = 0;
   out_4702066556653843398[244] = 0;
   out_4702066556653843398[245] = 0;
   out_4702066556653843398[246] = 0;
   out_4702066556653843398[247] = 1;
   out_4702066556653843398[248] = 0;
   out_4702066556653843398[249] = 0;
   out_4702066556653843398[250] = 0;
   out_4702066556653843398[251] = 0;
   out_4702066556653843398[252] = 0;
   out_4702066556653843398[253] = 0;
   out_4702066556653843398[254] = 0;
   out_4702066556653843398[255] = 0;
   out_4702066556653843398[256] = 0;
   out_4702066556653843398[257] = 0;
   out_4702066556653843398[258] = 0;
   out_4702066556653843398[259] = 0;
   out_4702066556653843398[260] = 0;
   out_4702066556653843398[261] = 0;
   out_4702066556653843398[262] = 0;
   out_4702066556653843398[263] = 0;
   out_4702066556653843398[264] = 0;
   out_4702066556653843398[265] = 0;
   out_4702066556653843398[266] = 1;
   out_4702066556653843398[267] = 0;
   out_4702066556653843398[268] = 0;
   out_4702066556653843398[269] = 0;
   out_4702066556653843398[270] = 0;
   out_4702066556653843398[271] = 0;
   out_4702066556653843398[272] = 0;
   out_4702066556653843398[273] = 0;
   out_4702066556653843398[274] = 0;
   out_4702066556653843398[275] = 0;
   out_4702066556653843398[276] = 0;
   out_4702066556653843398[277] = 0;
   out_4702066556653843398[278] = 0;
   out_4702066556653843398[279] = 0;
   out_4702066556653843398[280] = 0;
   out_4702066556653843398[281] = 0;
   out_4702066556653843398[282] = 0;
   out_4702066556653843398[283] = 0;
   out_4702066556653843398[284] = 0;
   out_4702066556653843398[285] = 1;
   out_4702066556653843398[286] = 0;
   out_4702066556653843398[287] = 0;
   out_4702066556653843398[288] = 0;
   out_4702066556653843398[289] = 0;
   out_4702066556653843398[290] = 0;
   out_4702066556653843398[291] = 0;
   out_4702066556653843398[292] = 0;
   out_4702066556653843398[293] = 0;
   out_4702066556653843398[294] = 0;
   out_4702066556653843398[295] = 0;
   out_4702066556653843398[296] = 0;
   out_4702066556653843398[297] = 0;
   out_4702066556653843398[298] = 0;
   out_4702066556653843398[299] = 0;
   out_4702066556653843398[300] = 0;
   out_4702066556653843398[301] = 0;
   out_4702066556653843398[302] = 0;
   out_4702066556653843398[303] = 0;
   out_4702066556653843398[304] = 1;
   out_4702066556653843398[305] = 0;
   out_4702066556653843398[306] = 0;
   out_4702066556653843398[307] = 0;
   out_4702066556653843398[308] = 0;
   out_4702066556653843398[309] = 0;
   out_4702066556653843398[310] = 0;
   out_4702066556653843398[311] = 0;
   out_4702066556653843398[312] = 0;
   out_4702066556653843398[313] = 0;
   out_4702066556653843398[314] = 0;
   out_4702066556653843398[315] = 0;
   out_4702066556653843398[316] = 0;
   out_4702066556653843398[317] = 0;
   out_4702066556653843398[318] = 0;
   out_4702066556653843398[319] = 0;
   out_4702066556653843398[320] = 0;
   out_4702066556653843398[321] = 0;
   out_4702066556653843398[322] = 0;
   out_4702066556653843398[323] = 1;
}
void h_4(double *state, double *unused, double *out_6137997042648778710) {
   out_6137997042648778710[0] = state[6] + state[9];
   out_6137997042648778710[1] = state[7] + state[10];
   out_6137997042648778710[2] = state[8] + state[11];
}
void H_4(double *state, double *unused, double *out_5403932535851547528) {
   out_5403932535851547528[0] = 0;
   out_5403932535851547528[1] = 0;
   out_5403932535851547528[2] = 0;
   out_5403932535851547528[3] = 0;
   out_5403932535851547528[4] = 0;
   out_5403932535851547528[5] = 0;
   out_5403932535851547528[6] = 1;
   out_5403932535851547528[7] = 0;
   out_5403932535851547528[8] = 0;
   out_5403932535851547528[9] = 1;
   out_5403932535851547528[10] = 0;
   out_5403932535851547528[11] = 0;
   out_5403932535851547528[12] = 0;
   out_5403932535851547528[13] = 0;
   out_5403932535851547528[14] = 0;
   out_5403932535851547528[15] = 0;
   out_5403932535851547528[16] = 0;
   out_5403932535851547528[17] = 0;
   out_5403932535851547528[18] = 0;
   out_5403932535851547528[19] = 0;
   out_5403932535851547528[20] = 0;
   out_5403932535851547528[21] = 0;
   out_5403932535851547528[22] = 0;
   out_5403932535851547528[23] = 0;
   out_5403932535851547528[24] = 0;
   out_5403932535851547528[25] = 1;
   out_5403932535851547528[26] = 0;
   out_5403932535851547528[27] = 0;
   out_5403932535851547528[28] = 1;
   out_5403932535851547528[29] = 0;
   out_5403932535851547528[30] = 0;
   out_5403932535851547528[31] = 0;
   out_5403932535851547528[32] = 0;
   out_5403932535851547528[33] = 0;
   out_5403932535851547528[34] = 0;
   out_5403932535851547528[35] = 0;
   out_5403932535851547528[36] = 0;
   out_5403932535851547528[37] = 0;
   out_5403932535851547528[38] = 0;
   out_5403932535851547528[39] = 0;
   out_5403932535851547528[40] = 0;
   out_5403932535851547528[41] = 0;
   out_5403932535851547528[42] = 0;
   out_5403932535851547528[43] = 0;
   out_5403932535851547528[44] = 1;
   out_5403932535851547528[45] = 0;
   out_5403932535851547528[46] = 0;
   out_5403932535851547528[47] = 1;
   out_5403932535851547528[48] = 0;
   out_5403932535851547528[49] = 0;
   out_5403932535851547528[50] = 0;
   out_5403932535851547528[51] = 0;
   out_5403932535851547528[52] = 0;
   out_5403932535851547528[53] = 0;
}
void h_10(double *state, double *unused, double *out_5824027401609001493) {
   out_5824027401609001493[0] = 9.8100000000000005*sin(state[1]) - state[4]*state[8] + state[5]*state[7] + state[12] + state[15];
   out_5824027401609001493[1] = -9.8100000000000005*sin(state[0])*cos(state[1]) + state[3]*state[8] - state[5]*state[6] + state[13] + state[16];
   out_5824027401609001493[2] = -9.8100000000000005*cos(state[0])*cos(state[1]) - state[3]*state[7] + state[4]*state[6] + state[14] + state[17];
}
void H_10(double *state, double *unused, double *out_5647838180481634355) {
   out_5647838180481634355[0] = 0;
   out_5647838180481634355[1] = 9.8100000000000005*cos(state[1]);
   out_5647838180481634355[2] = 0;
   out_5647838180481634355[3] = 0;
   out_5647838180481634355[4] = -state[8];
   out_5647838180481634355[5] = state[7];
   out_5647838180481634355[6] = 0;
   out_5647838180481634355[7] = state[5];
   out_5647838180481634355[8] = -state[4];
   out_5647838180481634355[9] = 0;
   out_5647838180481634355[10] = 0;
   out_5647838180481634355[11] = 0;
   out_5647838180481634355[12] = 1;
   out_5647838180481634355[13] = 0;
   out_5647838180481634355[14] = 0;
   out_5647838180481634355[15] = 1;
   out_5647838180481634355[16] = 0;
   out_5647838180481634355[17] = 0;
   out_5647838180481634355[18] = -9.8100000000000005*cos(state[0])*cos(state[1]);
   out_5647838180481634355[19] = 9.8100000000000005*sin(state[0])*sin(state[1]);
   out_5647838180481634355[20] = 0;
   out_5647838180481634355[21] = state[8];
   out_5647838180481634355[22] = 0;
   out_5647838180481634355[23] = -state[6];
   out_5647838180481634355[24] = -state[5];
   out_5647838180481634355[25] = 0;
   out_5647838180481634355[26] = state[3];
   out_5647838180481634355[27] = 0;
   out_5647838180481634355[28] = 0;
   out_5647838180481634355[29] = 0;
   out_5647838180481634355[30] = 0;
   out_5647838180481634355[31] = 1;
   out_5647838180481634355[32] = 0;
   out_5647838180481634355[33] = 0;
   out_5647838180481634355[34] = 1;
   out_5647838180481634355[35] = 0;
   out_5647838180481634355[36] = 9.8100000000000005*sin(state[0])*cos(state[1]);
   out_5647838180481634355[37] = 9.8100000000000005*sin(state[1])*cos(state[0]);
   out_5647838180481634355[38] = 0;
   out_5647838180481634355[39] = -state[7];
   out_5647838180481634355[40] = state[6];
   out_5647838180481634355[41] = 0;
   out_5647838180481634355[42] = state[4];
   out_5647838180481634355[43] = -state[3];
   out_5647838180481634355[44] = 0;
   out_5647838180481634355[45] = 0;
   out_5647838180481634355[46] = 0;
   out_5647838180481634355[47] = 0;
   out_5647838180481634355[48] = 0;
   out_5647838180481634355[49] = 0;
   out_5647838180481634355[50] = 1;
   out_5647838180481634355[51] = 0;
   out_5647838180481634355[52] = 0;
   out_5647838180481634355[53] = 1;
}
void h_13(double *state, double *unused, double *out_5389816574077237163) {
   out_5389816574077237163[0] = state[3];
   out_5389816574077237163[1] = state[4];
   out_5389816574077237163[2] = state[5];
}
void H_13(double *state, double *unused, double *out_8616206361183880329) {
   out_8616206361183880329[0] = 0;
   out_8616206361183880329[1] = 0;
   out_8616206361183880329[2] = 0;
   out_8616206361183880329[3] = 1;
   out_8616206361183880329[4] = 0;
   out_8616206361183880329[5] = 0;
   out_8616206361183880329[6] = 0;
   out_8616206361183880329[7] = 0;
   out_8616206361183880329[8] = 0;
   out_8616206361183880329[9] = 0;
   out_8616206361183880329[10] = 0;
   out_8616206361183880329[11] = 0;
   out_8616206361183880329[12] = 0;
   out_8616206361183880329[13] = 0;
   out_8616206361183880329[14] = 0;
   out_8616206361183880329[15] = 0;
   out_8616206361183880329[16] = 0;
   out_8616206361183880329[17] = 0;
   out_8616206361183880329[18] = 0;
   out_8616206361183880329[19] = 0;
   out_8616206361183880329[20] = 0;
   out_8616206361183880329[21] = 0;
   out_8616206361183880329[22] = 1;
   out_8616206361183880329[23] = 0;
   out_8616206361183880329[24] = 0;
   out_8616206361183880329[25] = 0;
   out_8616206361183880329[26] = 0;
   out_8616206361183880329[27] = 0;
   out_8616206361183880329[28] = 0;
   out_8616206361183880329[29] = 0;
   out_8616206361183880329[30] = 0;
   out_8616206361183880329[31] = 0;
   out_8616206361183880329[32] = 0;
   out_8616206361183880329[33] = 0;
   out_8616206361183880329[34] = 0;
   out_8616206361183880329[35] = 0;
   out_8616206361183880329[36] = 0;
   out_8616206361183880329[37] = 0;
   out_8616206361183880329[38] = 0;
   out_8616206361183880329[39] = 0;
   out_8616206361183880329[40] = 0;
   out_8616206361183880329[41] = 1;
   out_8616206361183880329[42] = 0;
   out_8616206361183880329[43] = 0;
   out_8616206361183880329[44] = 0;
   out_8616206361183880329[45] = 0;
   out_8616206361183880329[46] = 0;
   out_8616206361183880329[47] = 0;
   out_8616206361183880329[48] = 0;
   out_8616206361183880329[49] = 0;
   out_8616206361183880329[50] = 0;
   out_8616206361183880329[51] = 0;
   out_8616206361183880329[52] = 0;
   out_8616206361183880329[53] = 0;
}
void h_14(double *state, double *unused, double *out_364380652379967511) {
   out_364380652379967511[0] = state[6];
   out_364380652379967511[1] = state[7];
   out_364380652379967511[2] = state[8];
}
void H_14(double *state, double *unused, double *out_9079570681518519559) {
   out_9079570681518519559[0] = 0;
   out_9079570681518519559[1] = 0;
   out_9079570681518519559[2] = 0;
   out_9079570681518519559[3] = 0;
   out_9079570681518519559[4] = 0;
   out_9079570681518519559[5] = 0;
   out_9079570681518519559[6] = 1;
   out_9079570681518519559[7] = 0;
   out_9079570681518519559[8] = 0;
   out_9079570681518519559[9] = 0;
   out_9079570681518519559[10] = 0;
   out_9079570681518519559[11] = 0;
   out_9079570681518519559[12] = 0;
   out_9079570681518519559[13] = 0;
   out_9079570681518519559[14] = 0;
   out_9079570681518519559[15] = 0;
   out_9079570681518519559[16] = 0;
   out_9079570681518519559[17] = 0;
   out_9079570681518519559[18] = 0;
   out_9079570681518519559[19] = 0;
   out_9079570681518519559[20] = 0;
   out_9079570681518519559[21] = 0;
   out_9079570681518519559[22] = 0;
   out_9079570681518519559[23] = 0;
   out_9079570681518519559[24] = 0;
   out_9079570681518519559[25] = 1;
   out_9079570681518519559[26] = 0;
   out_9079570681518519559[27] = 0;
   out_9079570681518519559[28] = 0;
   out_9079570681518519559[29] = 0;
   out_9079570681518519559[30] = 0;
   out_9079570681518519559[31] = 0;
   out_9079570681518519559[32] = 0;
   out_9079570681518519559[33] = 0;
   out_9079570681518519559[34] = 0;
   out_9079570681518519559[35] = 0;
   out_9079570681518519559[36] = 0;
   out_9079570681518519559[37] = 0;
   out_9079570681518519559[38] = 0;
   out_9079570681518519559[39] = 0;
   out_9079570681518519559[40] = 0;
   out_9079570681518519559[41] = 0;
   out_9079570681518519559[42] = 0;
   out_9079570681518519559[43] = 0;
   out_9079570681518519559[44] = 1;
   out_9079570681518519559[45] = 0;
   out_9079570681518519559[46] = 0;
   out_9079570681518519559[47] = 0;
   out_9079570681518519559[48] = 0;
   out_9079570681518519559[49] = 0;
   out_9079570681518519559[50] = 0;
   out_9079570681518519559[51] = 0;
   out_9079570681518519559[52] = 0;
   out_9079570681518519559[53] = 0;
}
#include <eigen3/Eigen/Dense>
#include <iostream>

typedef Eigen::Matrix<double, DIM, DIM, Eigen::RowMajor> DDM;
typedef Eigen::Matrix<double, EDIM, EDIM, Eigen::RowMajor> EEM;
typedef Eigen::Matrix<double, DIM, EDIM, Eigen::RowMajor> DEM;

void predict(double *in_x, double *in_P, double *in_Q, double dt) {
  typedef Eigen::Matrix<double, MEDIM, MEDIM, Eigen::RowMajor> RRM;

  double nx[DIM] = {0};
  double in_F[EDIM*EDIM] = {0};

  // functions from sympy
  f_fun(in_x, dt, nx);
  F_fun(in_x, dt, in_F);


  EEM F(in_F);
  EEM P(in_P);
  EEM Q(in_Q);

  RRM F_main = F.topLeftCorner(MEDIM, MEDIM);
  P.topLeftCorner(MEDIM, MEDIM) = (F_main * P.topLeftCorner(MEDIM, MEDIM)) * F_main.transpose();
  P.topRightCorner(MEDIM, EDIM - MEDIM) = F_main * P.topRightCorner(MEDIM, EDIM - MEDIM);
  P.bottomLeftCorner(EDIM - MEDIM, MEDIM) = P.bottomLeftCorner(EDIM - MEDIM, MEDIM) * F_main.transpose();

  P = P + dt*Q;

  // copy out state
  memcpy(in_x, nx, DIM * sizeof(double));
  memcpy(in_P, P.data(), EDIM * EDIM * sizeof(double));
}

// note: extra_args dim only correct when null space projecting
// otherwise 1
template <int ZDIM, int EADIM, bool MAHA_TEST>
void update(double *in_x, double *in_P, Hfun h_fun, Hfun H_fun, Hfun Hea_fun, double *in_z, double *in_R, double *in_ea, double MAHA_THRESHOLD) {
  typedef Eigen::Matrix<double, ZDIM, ZDIM, Eigen::RowMajor> ZZM;
  typedef Eigen::Matrix<double, ZDIM, DIM, Eigen::RowMajor> ZDM;
  typedef Eigen::Matrix<double, Eigen::Dynamic, EDIM, Eigen::RowMajor> XEM;
  //typedef Eigen::Matrix<double, EDIM, ZDIM, Eigen::RowMajor> EZM;
  typedef Eigen::Matrix<double, Eigen::Dynamic, 1> X1M;
  typedef Eigen::Matrix<double, Eigen::Dynamic, Eigen::Dynamic, Eigen::RowMajor> XXM;

  double in_hx[ZDIM] = {0};
  double in_H[ZDIM * DIM] = {0};
  double in_H_mod[EDIM * DIM] = {0};
  double delta_x[EDIM] = {0};
  double x_new[DIM] = {0};


  // state x, P
  Eigen::Matrix<double, ZDIM, 1> z(in_z);
  EEM P(in_P);
  ZZM pre_R(in_R);

  // functions from sympy
  h_fun(in_x, in_ea, in_hx);
  H_fun(in_x, in_ea, in_H);
  ZDM pre_H(in_H);

  // get y (y = z - hx)
  Eigen::Matrix<double, ZDIM, 1> pre_y(in_hx); pre_y = z - pre_y;
  X1M y; XXM H; XXM R;
  if (Hea_fun){
    typedef Eigen::Matrix<double, ZDIM, EADIM, Eigen::RowMajor> ZAM;
    double in_Hea[ZDIM * EADIM] = {0};
    Hea_fun(in_x, in_ea, in_Hea);
    ZAM Hea(in_Hea);
    XXM A = Hea.transpose().fullPivLu().kernel();


    y = A.transpose() * pre_y;
    H = A.transpose() * pre_H;
    R = A.transpose() * pre_R * A;
  } else {
    y = pre_y;
    H = pre_H;
    R = pre_R;
  }
  // get modified H
  H_mod_fun(in_x, in_H_mod);
  DEM H_mod(in_H_mod);
  XEM H_err = H * H_mod;

  // Do mahalobis distance test
  if (MAHA_TEST){
    XXM a = (H_err * P * H_err.transpose() + R).inverse();
    double maha_dist = y.transpose() * a * y;
    if (maha_dist > MAHA_THRESHOLD){
      R = 1.0e16 * R;
    }
  }

  // Outlier resilient weighting
  double weight = 1;//(1.5)/(1 + y.squaredNorm()/R.sum());

  // kalman gains and I_KH
  XXM S = ((H_err * P) * H_err.transpose()) + R/weight;
  XEM KT = S.fullPivLu().solve(H_err * P.transpose());
  //EZM K = KT.transpose(); TODO: WHY DOES THIS NOT COMPILE?
  //EZM K = S.fullPivLu().solve(H_err * P.transpose()).transpose();
  //std::cout << "Here is the matrix rot:\n" << K << std::endl;
  EEM I_KH = Eigen::Matrix<double, EDIM, EDIM>::Identity() - (KT.transpose() * H_err);

  // update state by injecting dx
  Eigen::Matrix<double, EDIM, 1> dx(delta_x);
  dx  = (KT.transpose() * y);
  memcpy(delta_x, dx.data(), EDIM * sizeof(double));
  err_fun(in_x, delta_x, x_new);
  Eigen::Matrix<double, DIM, 1> x(x_new);

  // update cov
  P = ((I_KH * P) * I_KH.transpose()) + ((KT.transpose() * R) * KT);

  // copy out state
  memcpy(in_x, x.data(), DIM * sizeof(double));
  memcpy(in_P, P.data(), EDIM * EDIM * sizeof(double));
  memcpy(in_z, y.data(), y.rows() * sizeof(double));
}




}
extern "C" {

void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<3, 3, 0>(in_x, in_P, h_4, H_4, NULL, in_z, in_R, in_ea, MAHA_THRESH_4);
}
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<3, 3, 0>(in_x, in_P, h_10, H_10, NULL, in_z, in_R, in_ea, MAHA_THRESH_10);
}
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<3, 3, 0>(in_x, in_P, h_13, H_13, NULL, in_z, in_R, in_ea, MAHA_THRESH_13);
}
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<3, 3, 0>(in_x, in_P, h_14, H_14, NULL, in_z, in_R, in_ea, MAHA_THRESH_14);
}
void pose_err_fun(double *nom_x, double *delta_x, double *out_5818094549552656547) {
  err_fun(nom_x, delta_x, out_5818094549552656547);
}
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_3606049234714008263) {
  inv_err_fun(nom_x, true_x, out_3606049234714008263);
}
void pose_H_mod_fun(double *state, double *out_1632125326007639956) {
  H_mod_fun(state, out_1632125326007639956);
}
void pose_f_fun(double *state, double dt, double *out_6251314416692735066) {
  f_fun(state,  dt, out_6251314416692735066);
}
void pose_F_fun(double *state, double dt, double *out_4702066556653843398) {
  F_fun(state,  dt, out_4702066556653843398);
}
void pose_h_4(double *state, double *unused, double *out_6137997042648778710) {
  h_4(state, unused, out_6137997042648778710);
}
void pose_H_4(double *state, double *unused, double *out_5403932535851547528) {
  H_4(state, unused, out_5403932535851547528);
}
void pose_h_10(double *state, double *unused, double *out_5824027401609001493) {
  h_10(state, unused, out_5824027401609001493);
}
void pose_H_10(double *state, double *unused, double *out_5647838180481634355) {
  H_10(state, unused, out_5647838180481634355);
}
void pose_h_13(double *state, double *unused, double *out_5389816574077237163) {
  h_13(state, unused, out_5389816574077237163);
}
void pose_H_13(double *state, double *unused, double *out_8616206361183880329) {
  H_13(state, unused, out_8616206361183880329);
}
void pose_h_14(double *state, double *unused, double *out_364380652379967511) {
  h_14(state, unused, out_364380652379967511);
}
void pose_H_14(double *state, double *unused, double *out_9079570681518519559) {
  H_14(state, unused, out_9079570681518519559);
}
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt) {
  predict(in_x, in_P, in_Q, dt);
}
}

const EKF pose = {
  .name = "pose",
  .kinds = { 4, 10, 13, 14 },
  .feature_kinds = {  },
  .f_fun = pose_f_fun,
  .F_fun = pose_F_fun,
  .err_fun = pose_err_fun,
  .inv_err_fun = pose_inv_err_fun,
  .H_mod_fun = pose_H_mod_fun,
  .predict = pose_predict,
  .hs = {
    { 4, pose_h_4 },
    { 10, pose_h_10 },
    { 13, pose_h_13 },
    { 14, pose_h_14 },
  },
  .Hs = {
    { 4, pose_H_4 },
    { 10, pose_H_10 },
    { 13, pose_H_13 },
    { 14, pose_H_14 },
  },
  .updates = {
    { 4, pose_update_4 },
    { 10, pose_update_10 },
    { 13, pose_update_13 },
    { 14, pose_update_14 },
  },
  .Hes = {
  },
  .sets = {
  },
  .extra_routines = {
  },
};

ekf_lib_init(pose)
