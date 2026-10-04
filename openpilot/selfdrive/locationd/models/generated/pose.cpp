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
void err_fun(double *nom_x, double *delta_x, double *out_7161146668565307749) {
   out_7161146668565307749[0] = delta_x[0] + nom_x[0];
   out_7161146668565307749[1] = delta_x[1] + nom_x[1];
   out_7161146668565307749[2] = delta_x[2] + nom_x[2];
   out_7161146668565307749[3] = delta_x[3] + nom_x[3];
   out_7161146668565307749[4] = delta_x[4] + nom_x[4];
   out_7161146668565307749[5] = delta_x[5] + nom_x[5];
   out_7161146668565307749[6] = delta_x[6] + nom_x[6];
   out_7161146668565307749[7] = delta_x[7] + nom_x[7];
   out_7161146668565307749[8] = delta_x[8] + nom_x[8];
   out_7161146668565307749[9] = delta_x[9] + nom_x[9];
   out_7161146668565307749[10] = delta_x[10] + nom_x[10];
   out_7161146668565307749[11] = delta_x[11] + nom_x[11];
   out_7161146668565307749[12] = delta_x[12] + nom_x[12];
   out_7161146668565307749[13] = delta_x[13] + nom_x[13];
   out_7161146668565307749[14] = delta_x[14] + nom_x[14];
   out_7161146668565307749[15] = delta_x[15] + nom_x[15];
   out_7161146668565307749[16] = delta_x[16] + nom_x[16];
   out_7161146668565307749[17] = delta_x[17] + nom_x[17];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_9192799682543864141) {
   out_9192799682543864141[0] = -nom_x[0] + true_x[0];
   out_9192799682543864141[1] = -nom_x[1] + true_x[1];
   out_9192799682543864141[2] = -nom_x[2] + true_x[2];
   out_9192799682543864141[3] = -nom_x[3] + true_x[3];
   out_9192799682543864141[4] = -nom_x[4] + true_x[4];
   out_9192799682543864141[5] = -nom_x[5] + true_x[5];
   out_9192799682543864141[6] = -nom_x[6] + true_x[6];
   out_9192799682543864141[7] = -nom_x[7] + true_x[7];
   out_9192799682543864141[8] = -nom_x[8] + true_x[8];
   out_9192799682543864141[9] = -nom_x[9] + true_x[9];
   out_9192799682543864141[10] = -nom_x[10] + true_x[10];
   out_9192799682543864141[11] = -nom_x[11] + true_x[11];
   out_9192799682543864141[12] = -nom_x[12] + true_x[12];
   out_9192799682543864141[13] = -nom_x[13] + true_x[13];
   out_9192799682543864141[14] = -nom_x[14] + true_x[14];
   out_9192799682543864141[15] = -nom_x[15] + true_x[15];
   out_9192799682543864141[16] = -nom_x[16] + true_x[16];
   out_9192799682543864141[17] = -nom_x[17] + true_x[17];
}
void H_mod_fun(double *state, double *out_7855275330575582361) {
   out_7855275330575582361[0] = 1.0;
   out_7855275330575582361[1] = 0.0;
   out_7855275330575582361[2] = 0.0;
   out_7855275330575582361[3] = 0.0;
   out_7855275330575582361[4] = 0.0;
   out_7855275330575582361[5] = 0.0;
   out_7855275330575582361[6] = 0.0;
   out_7855275330575582361[7] = 0.0;
   out_7855275330575582361[8] = 0.0;
   out_7855275330575582361[9] = 0.0;
   out_7855275330575582361[10] = 0.0;
   out_7855275330575582361[11] = 0.0;
   out_7855275330575582361[12] = 0.0;
   out_7855275330575582361[13] = 0.0;
   out_7855275330575582361[14] = 0.0;
   out_7855275330575582361[15] = 0.0;
   out_7855275330575582361[16] = 0.0;
   out_7855275330575582361[17] = 0.0;
   out_7855275330575582361[18] = 0.0;
   out_7855275330575582361[19] = 1.0;
   out_7855275330575582361[20] = 0.0;
   out_7855275330575582361[21] = 0.0;
   out_7855275330575582361[22] = 0.0;
   out_7855275330575582361[23] = 0.0;
   out_7855275330575582361[24] = 0.0;
   out_7855275330575582361[25] = 0.0;
   out_7855275330575582361[26] = 0.0;
   out_7855275330575582361[27] = 0.0;
   out_7855275330575582361[28] = 0.0;
   out_7855275330575582361[29] = 0.0;
   out_7855275330575582361[30] = 0.0;
   out_7855275330575582361[31] = 0.0;
   out_7855275330575582361[32] = 0.0;
   out_7855275330575582361[33] = 0.0;
   out_7855275330575582361[34] = 0.0;
   out_7855275330575582361[35] = 0.0;
   out_7855275330575582361[36] = 0.0;
   out_7855275330575582361[37] = 0.0;
   out_7855275330575582361[38] = 1.0;
   out_7855275330575582361[39] = 0.0;
   out_7855275330575582361[40] = 0.0;
   out_7855275330575582361[41] = 0.0;
   out_7855275330575582361[42] = 0.0;
   out_7855275330575582361[43] = 0.0;
   out_7855275330575582361[44] = 0.0;
   out_7855275330575582361[45] = 0.0;
   out_7855275330575582361[46] = 0.0;
   out_7855275330575582361[47] = 0.0;
   out_7855275330575582361[48] = 0.0;
   out_7855275330575582361[49] = 0.0;
   out_7855275330575582361[50] = 0.0;
   out_7855275330575582361[51] = 0.0;
   out_7855275330575582361[52] = 0.0;
   out_7855275330575582361[53] = 0.0;
   out_7855275330575582361[54] = 0.0;
   out_7855275330575582361[55] = 0.0;
   out_7855275330575582361[56] = 0.0;
   out_7855275330575582361[57] = 1.0;
   out_7855275330575582361[58] = 0.0;
   out_7855275330575582361[59] = 0.0;
   out_7855275330575582361[60] = 0.0;
   out_7855275330575582361[61] = 0.0;
   out_7855275330575582361[62] = 0.0;
   out_7855275330575582361[63] = 0.0;
   out_7855275330575582361[64] = 0.0;
   out_7855275330575582361[65] = 0.0;
   out_7855275330575582361[66] = 0.0;
   out_7855275330575582361[67] = 0.0;
   out_7855275330575582361[68] = 0.0;
   out_7855275330575582361[69] = 0.0;
   out_7855275330575582361[70] = 0.0;
   out_7855275330575582361[71] = 0.0;
   out_7855275330575582361[72] = 0.0;
   out_7855275330575582361[73] = 0.0;
   out_7855275330575582361[74] = 0.0;
   out_7855275330575582361[75] = 0.0;
   out_7855275330575582361[76] = 1.0;
   out_7855275330575582361[77] = 0.0;
   out_7855275330575582361[78] = 0.0;
   out_7855275330575582361[79] = 0.0;
   out_7855275330575582361[80] = 0.0;
   out_7855275330575582361[81] = 0.0;
   out_7855275330575582361[82] = 0.0;
   out_7855275330575582361[83] = 0.0;
   out_7855275330575582361[84] = 0.0;
   out_7855275330575582361[85] = 0.0;
   out_7855275330575582361[86] = 0.0;
   out_7855275330575582361[87] = 0.0;
   out_7855275330575582361[88] = 0.0;
   out_7855275330575582361[89] = 0.0;
   out_7855275330575582361[90] = 0.0;
   out_7855275330575582361[91] = 0.0;
   out_7855275330575582361[92] = 0.0;
   out_7855275330575582361[93] = 0.0;
   out_7855275330575582361[94] = 0.0;
   out_7855275330575582361[95] = 1.0;
   out_7855275330575582361[96] = 0.0;
   out_7855275330575582361[97] = 0.0;
   out_7855275330575582361[98] = 0.0;
   out_7855275330575582361[99] = 0.0;
   out_7855275330575582361[100] = 0.0;
   out_7855275330575582361[101] = 0.0;
   out_7855275330575582361[102] = 0.0;
   out_7855275330575582361[103] = 0.0;
   out_7855275330575582361[104] = 0.0;
   out_7855275330575582361[105] = 0.0;
   out_7855275330575582361[106] = 0.0;
   out_7855275330575582361[107] = 0.0;
   out_7855275330575582361[108] = 0.0;
   out_7855275330575582361[109] = 0.0;
   out_7855275330575582361[110] = 0.0;
   out_7855275330575582361[111] = 0.0;
   out_7855275330575582361[112] = 0.0;
   out_7855275330575582361[113] = 0.0;
   out_7855275330575582361[114] = 1.0;
   out_7855275330575582361[115] = 0.0;
   out_7855275330575582361[116] = 0.0;
   out_7855275330575582361[117] = 0.0;
   out_7855275330575582361[118] = 0.0;
   out_7855275330575582361[119] = 0.0;
   out_7855275330575582361[120] = 0.0;
   out_7855275330575582361[121] = 0.0;
   out_7855275330575582361[122] = 0.0;
   out_7855275330575582361[123] = 0.0;
   out_7855275330575582361[124] = 0.0;
   out_7855275330575582361[125] = 0.0;
   out_7855275330575582361[126] = 0.0;
   out_7855275330575582361[127] = 0.0;
   out_7855275330575582361[128] = 0.0;
   out_7855275330575582361[129] = 0.0;
   out_7855275330575582361[130] = 0.0;
   out_7855275330575582361[131] = 0.0;
   out_7855275330575582361[132] = 0.0;
   out_7855275330575582361[133] = 1.0;
   out_7855275330575582361[134] = 0.0;
   out_7855275330575582361[135] = 0.0;
   out_7855275330575582361[136] = 0.0;
   out_7855275330575582361[137] = 0.0;
   out_7855275330575582361[138] = 0.0;
   out_7855275330575582361[139] = 0.0;
   out_7855275330575582361[140] = 0.0;
   out_7855275330575582361[141] = 0.0;
   out_7855275330575582361[142] = 0.0;
   out_7855275330575582361[143] = 0.0;
   out_7855275330575582361[144] = 0.0;
   out_7855275330575582361[145] = 0.0;
   out_7855275330575582361[146] = 0.0;
   out_7855275330575582361[147] = 0.0;
   out_7855275330575582361[148] = 0.0;
   out_7855275330575582361[149] = 0.0;
   out_7855275330575582361[150] = 0.0;
   out_7855275330575582361[151] = 0.0;
   out_7855275330575582361[152] = 1.0;
   out_7855275330575582361[153] = 0.0;
   out_7855275330575582361[154] = 0.0;
   out_7855275330575582361[155] = 0.0;
   out_7855275330575582361[156] = 0.0;
   out_7855275330575582361[157] = 0.0;
   out_7855275330575582361[158] = 0.0;
   out_7855275330575582361[159] = 0.0;
   out_7855275330575582361[160] = 0.0;
   out_7855275330575582361[161] = 0.0;
   out_7855275330575582361[162] = 0.0;
   out_7855275330575582361[163] = 0.0;
   out_7855275330575582361[164] = 0.0;
   out_7855275330575582361[165] = 0.0;
   out_7855275330575582361[166] = 0.0;
   out_7855275330575582361[167] = 0.0;
   out_7855275330575582361[168] = 0.0;
   out_7855275330575582361[169] = 0.0;
   out_7855275330575582361[170] = 0.0;
   out_7855275330575582361[171] = 1.0;
   out_7855275330575582361[172] = 0.0;
   out_7855275330575582361[173] = 0.0;
   out_7855275330575582361[174] = 0.0;
   out_7855275330575582361[175] = 0.0;
   out_7855275330575582361[176] = 0.0;
   out_7855275330575582361[177] = 0.0;
   out_7855275330575582361[178] = 0.0;
   out_7855275330575582361[179] = 0.0;
   out_7855275330575582361[180] = 0.0;
   out_7855275330575582361[181] = 0.0;
   out_7855275330575582361[182] = 0.0;
   out_7855275330575582361[183] = 0.0;
   out_7855275330575582361[184] = 0.0;
   out_7855275330575582361[185] = 0.0;
   out_7855275330575582361[186] = 0.0;
   out_7855275330575582361[187] = 0.0;
   out_7855275330575582361[188] = 0.0;
   out_7855275330575582361[189] = 0.0;
   out_7855275330575582361[190] = 1.0;
   out_7855275330575582361[191] = 0.0;
   out_7855275330575582361[192] = 0.0;
   out_7855275330575582361[193] = 0.0;
   out_7855275330575582361[194] = 0.0;
   out_7855275330575582361[195] = 0.0;
   out_7855275330575582361[196] = 0.0;
   out_7855275330575582361[197] = 0.0;
   out_7855275330575582361[198] = 0.0;
   out_7855275330575582361[199] = 0.0;
   out_7855275330575582361[200] = 0.0;
   out_7855275330575582361[201] = 0.0;
   out_7855275330575582361[202] = 0.0;
   out_7855275330575582361[203] = 0.0;
   out_7855275330575582361[204] = 0.0;
   out_7855275330575582361[205] = 0.0;
   out_7855275330575582361[206] = 0.0;
   out_7855275330575582361[207] = 0.0;
   out_7855275330575582361[208] = 0.0;
   out_7855275330575582361[209] = 1.0;
   out_7855275330575582361[210] = 0.0;
   out_7855275330575582361[211] = 0.0;
   out_7855275330575582361[212] = 0.0;
   out_7855275330575582361[213] = 0.0;
   out_7855275330575582361[214] = 0.0;
   out_7855275330575582361[215] = 0.0;
   out_7855275330575582361[216] = 0.0;
   out_7855275330575582361[217] = 0.0;
   out_7855275330575582361[218] = 0.0;
   out_7855275330575582361[219] = 0.0;
   out_7855275330575582361[220] = 0.0;
   out_7855275330575582361[221] = 0.0;
   out_7855275330575582361[222] = 0.0;
   out_7855275330575582361[223] = 0.0;
   out_7855275330575582361[224] = 0.0;
   out_7855275330575582361[225] = 0.0;
   out_7855275330575582361[226] = 0.0;
   out_7855275330575582361[227] = 0.0;
   out_7855275330575582361[228] = 1.0;
   out_7855275330575582361[229] = 0.0;
   out_7855275330575582361[230] = 0.0;
   out_7855275330575582361[231] = 0.0;
   out_7855275330575582361[232] = 0.0;
   out_7855275330575582361[233] = 0.0;
   out_7855275330575582361[234] = 0.0;
   out_7855275330575582361[235] = 0.0;
   out_7855275330575582361[236] = 0.0;
   out_7855275330575582361[237] = 0.0;
   out_7855275330575582361[238] = 0.0;
   out_7855275330575582361[239] = 0.0;
   out_7855275330575582361[240] = 0.0;
   out_7855275330575582361[241] = 0.0;
   out_7855275330575582361[242] = 0.0;
   out_7855275330575582361[243] = 0.0;
   out_7855275330575582361[244] = 0.0;
   out_7855275330575582361[245] = 0.0;
   out_7855275330575582361[246] = 0.0;
   out_7855275330575582361[247] = 1.0;
   out_7855275330575582361[248] = 0.0;
   out_7855275330575582361[249] = 0.0;
   out_7855275330575582361[250] = 0.0;
   out_7855275330575582361[251] = 0.0;
   out_7855275330575582361[252] = 0.0;
   out_7855275330575582361[253] = 0.0;
   out_7855275330575582361[254] = 0.0;
   out_7855275330575582361[255] = 0.0;
   out_7855275330575582361[256] = 0.0;
   out_7855275330575582361[257] = 0.0;
   out_7855275330575582361[258] = 0.0;
   out_7855275330575582361[259] = 0.0;
   out_7855275330575582361[260] = 0.0;
   out_7855275330575582361[261] = 0.0;
   out_7855275330575582361[262] = 0.0;
   out_7855275330575582361[263] = 0.0;
   out_7855275330575582361[264] = 0.0;
   out_7855275330575582361[265] = 0.0;
   out_7855275330575582361[266] = 1.0;
   out_7855275330575582361[267] = 0.0;
   out_7855275330575582361[268] = 0.0;
   out_7855275330575582361[269] = 0.0;
   out_7855275330575582361[270] = 0.0;
   out_7855275330575582361[271] = 0.0;
   out_7855275330575582361[272] = 0.0;
   out_7855275330575582361[273] = 0.0;
   out_7855275330575582361[274] = 0.0;
   out_7855275330575582361[275] = 0.0;
   out_7855275330575582361[276] = 0.0;
   out_7855275330575582361[277] = 0.0;
   out_7855275330575582361[278] = 0.0;
   out_7855275330575582361[279] = 0.0;
   out_7855275330575582361[280] = 0.0;
   out_7855275330575582361[281] = 0.0;
   out_7855275330575582361[282] = 0.0;
   out_7855275330575582361[283] = 0.0;
   out_7855275330575582361[284] = 0.0;
   out_7855275330575582361[285] = 1.0;
   out_7855275330575582361[286] = 0.0;
   out_7855275330575582361[287] = 0.0;
   out_7855275330575582361[288] = 0.0;
   out_7855275330575582361[289] = 0.0;
   out_7855275330575582361[290] = 0.0;
   out_7855275330575582361[291] = 0.0;
   out_7855275330575582361[292] = 0.0;
   out_7855275330575582361[293] = 0.0;
   out_7855275330575582361[294] = 0.0;
   out_7855275330575582361[295] = 0.0;
   out_7855275330575582361[296] = 0.0;
   out_7855275330575582361[297] = 0.0;
   out_7855275330575582361[298] = 0.0;
   out_7855275330575582361[299] = 0.0;
   out_7855275330575582361[300] = 0.0;
   out_7855275330575582361[301] = 0.0;
   out_7855275330575582361[302] = 0.0;
   out_7855275330575582361[303] = 0.0;
   out_7855275330575582361[304] = 1.0;
   out_7855275330575582361[305] = 0.0;
   out_7855275330575582361[306] = 0.0;
   out_7855275330575582361[307] = 0.0;
   out_7855275330575582361[308] = 0.0;
   out_7855275330575582361[309] = 0.0;
   out_7855275330575582361[310] = 0.0;
   out_7855275330575582361[311] = 0.0;
   out_7855275330575582361[312] = 0.0;
   out_7855275330575582361[313] = 0.0;
   out_7855275330575582361[314] = 0.0;
   out_7855275330575582361[315] = 0.0;
   out_7855275330575582361[316] = 0.0;
   out_7855275330575582361[317] = 0.0;
   out_7855275330575582361[318] = 0.0;
   out_7855275330575582361[319] = 0.0;
   out_7855275330575582361[320] = 0.0;
   out_7855275330575582361[321] = 0.0;
   out_7855275330575582361[322] = 0.0;
   out_7855275330575582361[323] = 1.0;
}
void f_fun(double *state, double dt, double *out_5704836990456063535) {
   out_5704836990456063535[0] = atan2((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), -(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]));
   out_5704836990456063535[1] = asin(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]));
   out_5704836990456063535[2] = atan2(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), -(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]));
   out_5704836990456063535[3] = dt*state[12] + state[3];
   out_5704836990456063535[4] = dt*state[13] + state[4];
   out_5704836990456063535[5] = dt*state[14] + state[5];
   out_5704836990456063535[6] = state[6];
   out_5704836990456063535[7] = state[7];
   out_5704836990456063535[8] = state[8];
   out_5704836990456063535[9] = state[9];
   out_5704836990456063535[10] = state[10];
   out_5704836990456063535[11] = state[11];
   out_5704836990456063535[12] = state[12];
   out_5704836990456063535[13] = state[13];
   out_5704836990456063535[14] = state[14];
   out_5704836990456063535[15] = state[15];
   out_5704836990456063535[16] = state[16];
   out_5704836990456063535[17] = state[17];
}
void F_fun(double *state, double dt, double *out_3943621887978734192) {
   out_3943621887978734192[0] = ((-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*cos(state[0])*cos(state[1]) - sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*cos(state[0])*cos(state[1]) - sin(dt*state[6])*sin(state[0])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_3943621887978734192[1] = ((-sin(dt*state[6])*sin(dt*state[8]) - sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*cos(state[1]) - (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*sin(state[1]) - sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(state[0]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*sin(state[1]) + (-sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) + sin(dt*state[8])*cos(dt*state[6]))*cos(state[1]) - sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(state[0]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_3943621887978734192[2] = 0;
   out_3943621887978734192[3] = 0;
   out_3943621887978734192[4] = 0;
   out_3943621887978734192[5] = 0;
   out_3943621887978734192[6] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(dt*cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) - dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_3943621887978734192[7] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*sin(dt*state[7])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[6])*sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) - dt*sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[7])*cos(dt*state[6])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[8])*sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]) - dt*sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_3943621887978734192[8] = ((dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((dt*sin(dt*state[6])*sin(dt*state[8]) + dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_3943621887978734192[9] = 0;
   out_3943621887978734192[10] = 0;
   out_3943621887978734192[11] = 0;
   out_3943621887978734192[12] = 0;
   out_3943621887978734192[13] = 0;
   out_3943621887978734192[14] = 0;
   out_3943621887978734192[15] = 0;
   out_3943621887978734192[16] = 0;
   out_3943621887978734192[17] = 0;
   out_3943621887978734192[18] = (-sin(dt*state[7])*sin(state[0])*cos(state[1]) - sin(dt*state[8])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_3943621887978734192[19] = (-sin(dt*state[7])*sin(state[1])*cos(state[0]) + sin(dt*state[8])*sin(state[0])*sin(state[1])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_3943621887978734192[20] = 0;
   out_3943621887978734192[21] = 0;
   out_3943621887978734192[22] = 0;
   out_3943621887978734192[23] = 0;
   out_3943621887978734192[24] = 0;
   out_3943621887978734192[25] = (dt*sin(dt*state[7])*sin(dt*state[8])*sin(state[0])*cos(state[1]) - dt*sin(dt*state[7])*sin(state[1])*cos(dt*state[8]) + dt*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_3943621887978734192[26] = (-dt*sin(dt*state[8])*sin(state[1])*cos(dt*state[7]) - dt*sin(state[0])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_3943621887978734192[27] = 0;
   out_3943621887978734192[28] = 0;
   out_3943621887978734192[29] = 0;
   out_3943621887978734192[30] = 0;
   out_3943621887978734192[31] = 0;
   out_3943621887978734192[32] = 0;
   out_3943621887978734192[33] = 0;
   out_3943621887978734192[34] = 0;
   out_3943621887978734192[35] = 0;
   out_3943621887978734192[36] = ((sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_3943621887978734192[37] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-sin(dt*state[7])*sin(state[2])*cos(state[0])*cos(state[1]) + sin(dt*state[8])*sin(state[0])*sin(state[2])*cos(dt*state[7])*cos(state[1]) - sin(state[1])*sin(state[2])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(-sin(dt*state[7])*cos(state[0])*cos(state[1])*cos(state[2]) + sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1])*cos(state[2]) - sin(state[1])*cos(dt*state[7])*cos(dt*state[8])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_3943621887978734192[38] = ((-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (-sin(state[0])*sin(state[1])*sin(state[2]) - cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_3943621887978734192[39] = 0;
   out_3943621887978734192[40] = 0;
   out_3943621887978734192[41] = 0;
   out_3943621887978734192[42] = 0;
   out_3943621887978734192[43] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(dt*(sin(state[0])*cos(state[2]) - sin(state[1])*sin(state[2])*cos(state[0]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*sin(state[2])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(dt*(-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_3943621887978734192[44] = (dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*sin(state[2])*cos(dt*state[7])*cos(state[1]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + (dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[7])*cos(state[1])*cos(state[2]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_3943621887978734192[45] = 0;
   out_3943621887978734192[46] = 0;
   out_3943621887978734192[47] = 0;
   out_3943621887978734192[48] = 0;
   out_3943621887978734192[49] = 0;
   out_3943621887978734192[50] = 0;
   out_3943621887978734192[51] = 0;
   out_3943621887978734192[52] = 0;
   out_3943621887978734192[53] = 0;
   out_3943621887978734192[54] = 0;
   out_3943621887978734192[55] = 0;
   out_3943621887978734192[56] = 0;
   out_3943621887978734192[57] = 1;
   out_3943621887978734192[58] = 0;
   out_3943621887978734192[59] = 0;
   out_3943621887978734192[60] = 0;
   out_3943621887978734192[61] = 0;
   out_3943621887978734192[62] = 0;
   out_3943621887978734192[63] = 0;
   out_3943621887978734192[64] = 0;
   out_3943621887978734192[65] = 0;
   out_3943621887978734192[66] = dt;
   out_3943621887978734192[67] = 0;
   out_3943621887978734192[68] = 0;
   out_3943621887978734192[69] = 0;
   out_3943621887978734192[70] = 0;
   out_3943621887978734192[71] = 0;
   out_3943621887978734192[72] = 0;
   out_3943621887978734192[73] = 0;
   out_3943621887978734192[74] = 0;
   out_3943621887978734192[75] = 0;
   out_3943621887978734192[76] = 1;
   out_3943621887978734192[77] = 0;
   out_3943621887978734192[78] = 0;
   out_3943621887978734192[79] = 0;
   out_3943621887978734192[80] = 0;
   out_3943621887978734192[81] = 0;
   out_3943621887978734192[82] = 0;
   out_3943621887978734192[83] = 0;
   out_3943621887978734192[84] = 0;
   out_3943621887978734192[85] = dt;
   out_3943621887978734192[86] = 0;
   out_3943621887978734192[87] = 0;
   out_3943621887978734192[88] = 0;
   out_3943621887978734192[89] = 0;
   out_3943621887978734192[90] = 0;
   out_3943621887978734192[91] = 0;
   out_3943621887978734192[92] = 0;
   out_3943621887978734192[93] = 0;
   out_3943621887978734192[94] = 0;
   out_3943621887978734192[95] = 1;
   out_3943621887978734192[96] = 0;
   out_3943621887978734192[97] = 0;
   out_3943621887978734192[98] = 0;
   out_3943621887978734192[99] = 0;
   out_3943621887978734192[100] = 0;
   out_3943621887978734192[101] = 0;
   out_3943621887978734192[102] = 0;
   out_3943621887978734192[103] = 0;
   out_3943621887978734192[104] = dt;
   out_3943621887978734192[105] = 0;
   out_3943621887978734192[106] = 0;
   out_3943621887978734192[107] = 0;
   out_3943621887978734192[108] = 0;
   out_3943621887978734192[109] = 0;
   out_3943621887978734192[110] = 0;
   out_3943621887978734192[111] = 0;
   out_3943621887978734192[112] = 0;
   out_3943621887978734192[113] = 0;
   out_3943621887978734192[114] = 1;
   out_3943621887978734192[115] = 0;
   out_3943621887978734192[116] = 0;
   out_3943621887978734192[117] = 0;
   out_3943621887978734192[118] = 0;
   out_3943621887978734192[119] = 0;
   out_3943621887978734192[120] = 0;
   out_3943621887978734192[121] = 0;
   out_3943621887978734192[122] = 0;
   out_3943621887978734192[123] = 0;
   out_3943621887978734192[124] = 0;
   out_3943621887978734192[125] = 0;
   out_3943621887978734192[126] = 0;
   out_3943621887978734192[127] = 0;
   out_3943621887978734192[128] = 0;
   out_3943621887978734192[129] = 0;
   out_3943621887978734192[130] = 0;
   out_3943621887978734192[131] = 0;
   out_3943621887978734192[132] = 0;
   out_3943621887978734192[133] = 1;
   out_3943621887978734192[134] = 0;
   out_3943621887978734192[135] = 0;
   out_3943621887978734192[136] = 0;
   out_3943621887978734192[137] = 0;
   out_3943621887978734192[138] = 0;
   out_3943621887978734192[139] = 0;
   out_3943621887978734192[140] = 0;
   out_3943621887978734192[141] = 0;
   out_3943621887978734192[142] = 0;
   out_3943621887978734192[143] = 0;
   out_3943621887978734192[144] = 0;
   out_3943621887978734192[145] = 0;
   out_3943621887978734192[146] = 0;
   out_3943621887978734192[147] = 0;
   out_3943621887978734192[148] = 0;
   out_3943621887978734192[149] = 0;
   out_3943621887978734192[150] = 0;
   out_3943621887978734192[151] = 0;
   out_3943621887978734192[152] = 1;
   out_3943621887978734192[153] = 0;
   out_3943621887978734192[154] = 0;
   out_3943621887978734192[155] = 0;
   out_3943621887978734192[156] = 0;
   out_3943621887978734192[157] = 0;
   out_3943621887978734192[158] = 0;
   out_3943621887978734192[159] = 0;
   out_3943621887978734192[160] = 0;
   out_3943621887978734192[161] = 0;
   out_3943621887978734192[162] = 0;
   out_3943621887978734192[163] = 0;
   out_3943621887978734192[164] = 0;
   out_3943621887978734192[165] = 0;
   out_3943621887978734192[166] = 0;
   out_3943621887978734192[167] = 0;
   out_3943621887978734192[168] = 0;
   out_3943621887978734192[169] = 0;
   out_3943621887978734192[170] = 0;
   out_3943621887978734192[171] = 1;
   out_3943621887978734192[172] = 0;
   out_3943621887978734192[173] = 0;
   out_3943621887978734192[174] = 0;
   out_3943621887978734192[175] = 0;
   out_3943621887978734192[176] = 0;
   out_3943621887978734192[177] = 0;
   out_3943621887978734192[178] = 0;
   out_3943621887978734192[179] = 0;
   out_3943621887978734192[180] = 0;
   out_3943621887978734192[181] = 0;
   out_3943621887978734192[182] = 0;
   out_3943621887978734192[183] = 0;
   out_3943621887978734192[184] = 0;
   out_3943621887978734192[185] = 0;
   out_3943621887978734192[186] = 0;
   out_3943621887978734192[187] = 0;
   out_3943621887978734192[188] = 0;
   out_3943621887978734192[189] = 0;
   out_3943621887978734192[190] = 1;
   out_3943621887978734192[191] = 0;
   out_3943621887978734192[192] = 0;
   out_3943621887978734192[193] = 0;
   out_3943621887978734192[194] = 0;
   out_3943621887978734192[195] = 0;
   out_3943621887978734192[196] = 0;
   out_3943621887978734192[197] = 0;
   out_3943621887978734192[198] = 0;
   out_3943621887978734192[199] = 0;
   out_3943621887978734192[200] = 0;
   out_3943621887978734192[201] = 0;
   out_3943621887978734192[202] = 0;
   out_3943621887978734192[203] = 0;
   out_3943621887978734192[204] = 0;
   out_3943621887978734192[205] = 0;
   out_3943621887978734192[206] = 0;
   out_3943621887978734192[207] = 0;
   out_3943621887978734192[208] = 0;
   out_3943621887978734192[209] = 1;
   out_3943621887978734192[210] = 0;
   out_3943621887978734192[211] = 0;
   out_3943621887978734192[212] = 0;
   out_3943621887978734192[213] = 0;
   out_3943621887978734192[214] = 0;
   out_3943621887978734192[215] = 0;
   out_3943621887978734192[216] = 0;
   out_3943621887978734192[217] = 0;
   out_3943621887978734192[218] = 0;
   out_3943621887978734192[219] = 0;
   out_3943621887978734192[220] = 0;
   out_3943621887978734192[221] = 0;
   out_3943621887978734192[222] = 0;
   out_3943621887978734192[223] = 0;
   out_3943621887978734192[224] = 0;
   out_3943621887978734192[225] = 0;
   out_3943621887978734192[226] = 0;
   out_3943621887978734192[227] = 0;
   out_3943621887978734192[228] = 1;
   out_3943621887978734192[229] = 0;
   out_3943621887978734192[230] = 0;
   out_3943621887978734192[231] = 0;
   out_3943621887978734192[232] = 0;
   out_3943621887978734192[233] = 0;
   out_3943621887978734192[234] = 0;
   out_3943621887978734192[235] = 0;
   out_3943621887978734192[236] = 0;
   out_3943621887978734192[237] = 0;
   out_3943621887978734192[238] = 0;
   out_3943621887978734192[239] = 0;
   out_3943621887978734192[240] = 0;
   out_3943621887978734192[241] = 0;
   out_3943621887978734192[242] = 0;
   out_3943621887978734192[243] = 0;
   out_3943621887978734192[244] = 0;
   out_3943621887978734192[245] = 0;
   out_3943621887978734192[246] = 0;
   out_3943621887978734192[247] = 1;
   out_3943621887978734192[248] = 0;
   out_3943621887978734192[249] = 0;
   out_3943621887978734192[250] = 0;
   out_3943621887978734192[251] = 0;
   out_3943621887978734192[252] = 0;
   out_3943621887978734192[253] = 0;
   out_3943621887978734192[254] = 0;
   out_3943621887978734192[255] = 0;
   out_3943621887978734192[256] = 0;
   out_3943621887978734192[257] = 0;
   out_3943621887978734192[258] = 0;
   out_3943621887978734192[259] = 0;
   out_3943621887978734192[260] = 0;
   out_3943621887978734192[261] = 0;
   out_3943621887978734192[262] = 0;
   out_3943621887978734192[263] = 0;
   out_3943621887978734192[264] = 0;
   out_3943621887978734192[265] = 0;
   out_3943621887978734192[266] = 1;
   out_3943621887978734192[267] = 0;
   out_3943621887978734192[268] = 0;
   out_3943621887978734192[269] = 0;
   out_3943621887978734192[270] = 0;
   out_3943621887978734192[271] = 0;
   out_3943621887978734192[272] = 0;
   out_3943621887978734192[273] = 0;
   out_3943621887978734192[274] = 0;
   out_3943621887978734192[275] = 0;
   out_3943621887978734192[276] = 0;
   out_3943621887978734192[277] = 0;
   out_3943621887978734192[278] = 0;
   out_3943621887978734192[279] = 0;
   out_3943621887978734192[280] = 0;
   out_3943621887978734192[281] = 0;
   out_3943621887978734192[282] = 0;
   out_3943621887978734192[283] = 0;
   out_3943621887978734192[284] = 0;
   out_3943621887978734192[285] = 1;
   out_3943621887978734192[286] = 0;
   out_3943621887978734192[287] = 0;
   out_3943621887978734192[288] = 0;
   out_3943621887978734192[289] = 0;
   out_3943621887978734192[290] = 0;
   out_3943621887978734192[291] = 0;
   out_3943621887978734192[292] = 0;
   out_3943621887978734192[293] = 0;
   out_3943621887978734192[294] = 0;
   out_3943621887978734192[295] = 0;
   out_3943621887978734192[296] = 0;
   out_3943621887978734192[297] = 0;
   out_3943621887978734192[298] = 0;
   out_3943621887978734192[299] = 0;
   out_3943621887978734192[300] = 0;
   out_3943621887978734192[301] = 0;
   out_3943621887978734192[302] = 0;
   out_3943621887978734192[303] = 0;
   out_3943621887978734192[304] = 1;
   out_3943621887978734192[305] = 0;
   out_3943621887978734192[306] = 0;
   out_3943621887978734192[307] = 0;
   out_3943621887978734192[308] = 0;
   out_3943621887978734192[309] = 0;
   out_3943621887978734192[310] = 0;
   out_3943621887978734192[311] = 0;
   out_3943621887978734192[312] = 0;
   out_3943621887978734192[313] = 0;
   out_3943621887978734192[314] = 0;
   out_3943621887978734192[315] = 0;
   out_3943621887978734192[316] = 0;
   out_3943621887978734192[317] = 0;
   out_3943621887978734192[318] = 0;
   out_3943621887978734192[319] = 0;
   out_3943621887978734192[320] = 0;
   out_3943621887978734192[321] = 0;
   out_3943621887978734192[322] = 0;
   out_3943621887978734192[323] = 1;
}
void h_4(double *state, double *unused, double *out_4630127890418963741) {
   out_4630127890418963741[0] = state[6] + state[9];
   out_4630127890418963741[1] = state[7] + state[10];
   out_4630127890418963741[2] = state[8] + state[11];
}
void H_4(double *state, double *unused, double *out_8609436332630294968) {
   out_8609436332630294968[0] = 0;
   out_8609436332630294968[1] = 0;
   out_8609436332630294968[2] = 0;
   out_8609436332630294968[3] = 0;
   out_8609436332630294968[4] = 0;
   out_8609436332630294968[5] = 0;
   out_8609436332630294968[6] = 1;
   out_8609436332630294968[7] = 0;
   out_8609436332630294968[8] = 0;
   out_8609436332630294968[9] = 1;
   out_8609436332630294968[10] = 0;
   out_8609436332630294968[11] = 0;
   out_8609436332630294968[12] = 0;
   out_8609436332630294968[13] = 0;
   out_8609436332630294968[14] = 0;
   out_8609436332630294968[15] = 0;
   out_8609436332630294968[16] = 0;
   out_8609436332630294968[17] = 0;
   out_8609436332630294968[18] = 0;
   out_8609436332630294968[19] = 0;
   out_8609436332630294968[20] = 0;
   out_8609436332630294968[21] = 0;
   out_8609436332630294968[22] = 0;
   out_8609436332630294968[23] = 0;
   out_8609436332630294968[24] = 0;
   out_8609436332630294968[25] = 1;
   out_8609436332630294968[26] = 0;
   out_8609436332630294968[27] = 0;
   out_8609436332630294968[28] = 1;
   out_8609436332630294968[29] = 0;
   out_8609436332630294968[30] = 0;
   out_8609436332630294968[31] = 0;
   out_8609436332630294968[32] = 0;
   out_8609436332630294968[33] = 0;
   out_8609436332630294968[34] = 0;
   out_8609436332630294968[35] = 0;
   out_8609436332630294968[36] = 0;
   out_8609436332630294968[37] = 0;
   out_8609436332630294968[38] = 0;
   out_8609436332630294968[39] = 0;
   out_8609436332630294968[40] = 0;
   out_8609436332630294968[41] = 0;
   out_8609436332630294968[42] = 0;
   out_8609436332630294968[43] = 0;
   out_8609436332630294968[44] = 1;
   out_8609436332630294968[45] = 0;
   out_8609436332630294968[46] = 0;
   out_8609436332630294968[47] = 1;
   out_8609436332630294968[48] = 0;
   out_8609436332630294968[49] = 0;
   out_8609436332630294968[50] = 0;
   out_8609436332630294968[51] = 0;
   out_8609436332630294968[52] = 0;
   out_8609436332630294968[53] = 0;
}
void h_10(double *state, double *unused, double *out_4053444435124290898) {
   out_4053444435124290898[0] = 9.8100000000000005*sin(state[1]) - state[4]*state[8] + state[5]*state[7] + state[12] + state[15];
   out_4053444435124290898[1] = -9.8100000000000005*sin(state[0])*cos(state[1]) + state[3]*state[8] - state[5]*state[6] + state[13] + state[16];
   out_4053444435124290898[2] = -9.8100000000000005*cos(state[0])*cos(state[1]) - state[3]*state[7] + state[4]*state[6] + state[14] + state[17];
}
void H_10(double *state, double *unused, double *out_1071649461987014282) {
   out_1071649461987014282[0] = 0;
   out_1071649461987014282[1] = 9.8100000000000005*cos(state[1]);
   out_1071649461987014282[2] = 0;
   out_1071649461987014282[3] = 0;
   out_1071649461987014282[4] = -state[8];
   out_1071649461987014282[5] = state[7];
   out_1071649461987014282[6] = 0;
   out_1071649461987014282[7] = state[5];
   out_1071649461987014282[8] = -state[4];
   out_1071649461987014282[9] = 0;
   out_1071649461987014282[10] = 0;
   out_1071649461987014282[11] = 0;
   out_1071649461987014282[12] = 1;
   out_1071649461987014282[13] = 0;
   out_1071649461987014282[14] = 0;
   out_1071649461987014282[15] = 1;
   out_1071649461987014282[16] = 0;
   out_1071649461987014282[17] = 0;
   out_1071649461987014282[18] = -9.8100000000000005*cos(state[0])*cos(state[1]);
   out_1071649461987014282[19] = 9.8100000000000005*sin(state[0])*sin(state[1]);
   out_1071649461987014282[20] = 0;
   out_1071649461987014282[21] = state[8];
   out_1071649461987014282[22] = 0;
   out_1071649461987014282[23] = -state[6];
   out_1071649461987014282[24] = -state[5];
   out_1071649461987014282[25] = 0;
   out_1071649461987014282[26] = state[3];
   out_1071649461987014282[27] = 0;
   out_1071649461987014282[28] = 0;
   out_1071649461987014282[29] = 0;
   out_1071649461987014282[30] = 0;
   out_1071649461987014282[31] = 1;
   out_1071649461987014282[32] = 0;
   out_1071649461987014282[33] = 0;
   out_1071649461987014282[34] = 1;
   out_1071649461987014282[35] = 0;
   out_1071649461987014282[36] = 9.8100000000000005*sin(state[0])*cos(state[1]);
   out_1071649461987014282[37] = 9.8100000000000005*sin(state[1])*cos(state[0]);
   out_1071649461987014282[38] = 0;
   out_1071649461987014282[39] = -state[7];
   out_1071649461987014282[40] = state[6];
   out_1071649461987014282[41] = 0;
   out_1071649461987014282[42] = state[4];
   out_1071649461987014282[43] = -state[3];
   out_1071649461987014282[44] = 0;
   out_1071649461987014282[45] = 0;
   out_1071649461987014282[46] = 0;
   out_1071649461987014282[47] = 0;
   out_1071649461987014282[48] = 0;
   out_1071649461987014282[49] = 0;
   out_1071649461987014282[50] = 1;
   out_1071649461987014282[51] = 0;
   out_1071649461987014282[52] = 0;
   out_1071649461987014282[53] = 1;
}
void h_13(double *state, double *unused, double *out_7118410191472981609) {
   out_7118410191472981609[0] = state[3];
   out_7118410191472981609[1] = state[4];
   out_7118410191472981609[2] = state[5];
}
void H_13(double *state, double *unused, double *out_2226676532762555719) {
   out_2226676532762555719[0] = 0;
   out_2226676532762555719[1] = 0;
   out_2226676532762555719[2] = 0;
   out_2226676532762555719[3] = 1;
   out_2226676532762555719[4] = 0;
   out_2226676532762555719[5] = 0;
   out_2226676532762555719[6] = 0;
   out_2226676532762555719[7] = 0;
   out_2226676532762555719[8] = 0;
   out_2226676532762555719[9] = 0;
   out_2226676532762555719[10] = 0;
   out_2226676532762555719[11] = 0;
   out_2226676532762555719[12] = 0;
   out_2226676532762555719[13] = 0;
   out_2226676532762555719[14] = 0;
   out_2226676532762555719[15] = 0;
   out_2226676532762555719[16] = 0;
   out_2226676532762555719[17] = 0;
   out_2226676532762555719[18] = 0;
   out_2226676532762555719[19] = 0;
   out_2226676532762555719[20] = 0;
   out_2226676532762555719[21] = 0;
   out_2226676532762555719[22] = 1;
   out_2226676532762555719[23] = 0;
   out_2226676532762555719[24] = 0;
   out_2226676532762555719[25] = 0;
   out_2226676532762555719[26] = 0;
   out_2226676532762555719[27] = 0;
   out_2226676532762555719[28] = 0;
   out_2226676532762555719[29] = 0;
   out_2226676532762555719[30] = 0;
   out_2226676532762555719[31] = 0;
   out_2226676532762555719[32] = 0;
   out_2226676532762555719[33] = 0;
   out_2226676532762555719[34] = 0;
   out_2226676532762555719[35] = 0;
   out_2226676532762555719[36] = 0;
   out_2226676532762555719[37] = 0;
   out_2226676532762555719[38] = 0;
   out_2226676532762555719[39] = 0;
   out_2226676532762555719[40] = 0;
   out_2226676532762555719[41] = 1;
   out_2226676532762555719[42] = 0;
   out_2226676532762555719[43] = 0;
   out_2226676532762555719[44] = 0;
   out_2226676532762555719[45] = 0;
   out_2226676532762555719[46] = 0;
   out_2226676532762555719[47] = 0;
   out_2226676532762555719[48] = 0;
   out_2226676532762555719[49] = 0;
   out_2226676532762555719[50] = 0;
   out_2226676532762555719[51] = 0;
   out_2226676532762555719[52] = 0;
   out_2226676532762555719[53] = 0;
}
void h_14(double *state, double *unused, double *out_4049122250011499148) {
   out_4049122250011499148[0] = state[6];
   out_4049122250011499148[1] = state[7];
   out_4049122250011499148[2] = state[8];
}
void H_14(double *state, double *unused, double *out_5526647900334922672) {
   out_5526647900334922672[0] = 0;
   out_5526647900334922672[1] = 0;
   out_5526647900334922672[2] = 0;
   out_5526647900334922672[3] = 0;
   out_5526647900334922672[4] = 0;
   out_5526647900334922672[5] = 0;
   out_5526647900334922672[6] = 1;
   out_5526647900334922672[7] = 0;
   out_5526647900334922672[8] = 0;
   out_5526647900334922672[9] = 0;
   out_5526647900334922672[10] = 0;
   out_5526647900334922672[11] = 0;
   out_5526647900334922672[12] = 0;
   out_5526647900334922672[13] = 0;
   out_5526647900334922672[14] = 0;
   out_5526647900334922672[15] = 0;
   out_5526647900334922672[16] = 0;
   out_5526647900334922672[17] = 0;
   out_5526647900334922672[18] = 0;
   out_5526647900334922672[19] = 0;
   out_5526647900334922672[20] = 0;
   out_5526647900334922672[21] = 0;
   out_5526647900334922672[22] = 0;
   out_5526647900334922672[23] = 0;
   out_5526647900334922672[24] = 0;
   out_5526647900334922672[25] = 1;
   out_5526647900334922672[26] = 0;
   out_5526647900334922672[27] = 0;
   out_5526647900334922672[28] = 0;
   out_5526647900334922672[29] = 0;
   out_5526647900334922672[30] = 0;
   out_5526647900334922672[31] = 0;
   out_5526647900334922672[32] = 0;
   out_5526647900334922672[33] = 0;
   out_5526647900334922672[34] = 0;
   out_5526647900334922672[35] = 0;
   out_5526647900334922672[36] = 0;
   out_5526647900334922672[37] = 0;
   out_5526647900334922672[38] = 0;
   out_5526647900334922672[39] = 0;
   out_5526647900334922672[40] = 0;
   out_5526647900334922672[41] = 0;
   out_5526647900334922672[42] = 0;
   out_5526647900334922672[43] = 0;
   out_5526647900334922672[44] = 1;
   out_5526647900334922672[45] = 0;
   out_5526647900334922672[46] = 0;
   out_5526647900334922672[47] = 0;
   out_5526647900334922672[48] = 0;
   out_5526647900334922672[49] = 0;
   out_5526647900334922672[50] = 0;
   out_5526647900334922672[51] = 0;
   out_5526647900334922672[52] = 0;
   out_5526647900334922672[53] = 0;
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
void pose_err_fun(double *nom_x, double *delta_x, double *out_7161146668565307749) {
  err_fun(nom_x, delta_x, out_7161146668565307749);
}
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_9192799682543864141) {
  inv_err_fun(nom_x, true_x, out_9192799682543864141);
}
void pose_H_mod_fun(double *state, double *out_7855275330575582361) {
  H_mod_fun(state, out_7855275330575582361);
}
void pose_f_fun(double *state, double dt, double *out_5704836990456063535) {
  f_fun(state,  dt, out_5704836990456063535);
}
void pose_F_fun(double *state, double dt, double *out_3943621887978734192) {
  F_fun(state,  dt, out_3943621887978734192);
}
void pose_h_4(double *state, double *unused, double *out_4630127890418963741) {
  h_4(state, unused, out_4630127890418963741);
}
void pose_H_4(double *state, double *unused, double *out_8609436332630294968) {
  H_4(state, unused, out_8609436332630294968);
}
void pose_h_10(double *state, double *unused, double *out_4053444435124290898) {
  h_10(state, unused, out_4053444435124290898);
}
void pose_H_10(double *state, double *unused, double *out_1071649461987014282) {
  H_10(state, unused, out_1071649461987014282);
}
void pose_h_13(double *state, double *unused, double *out_7118410191472981609) {
  h_13(state, unused, out_7118410191472981609);
}
void pose_H_13(double *state, double *unused, double *out_2226676532762555719) {
  H_13(state, unused, out_2226676532762555719);
}
void pose_h_14(double *state, double *unused, double *out_4049122250011499148) {
  h_14(state, unused, out_4049122250011499148);
}
void pose_H_14(double *state, double *unused, double *out_5526647900334922672) {
  H_14(state, unused, out_5526647900334922672);
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
