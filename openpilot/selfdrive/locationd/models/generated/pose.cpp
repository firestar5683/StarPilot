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
void err_fun(double *nom_x, double *delta_x, double *out_8327048500586505475) {
   out_8327048500586505475[0] = delta_x[0] + nom_x[0];
   out_8327048500586505475[1] = delta_x[1] + nom_x[1];
   out_8327048500586505475[2] = delta_x[2] + nom_x[2];
   out_8327048500586505475[3] = delta_x[3] + nom_x[3];
   out_8327048500586505475[4] = delta_x[4] + nom_x[4];
   out_8327048500586505475[5] = delta_x[5] + nom_x[5];
   out_8327048500586505475[6] = delta_x[6] + nom_x[6];
   out_8327048500586505475[7] = delta_x[7] + nom_x[7];
   out_8327048500586505475[8] = delta_x[8] + nom_x[8];
   out_8327048500586505475[9] = delta_x[9] + nom_x[9];
   out_8327048500586505475[10] = delta_x[10] + nom_x[10];
   out_8327048500586505475[11] = delta_x[11] + nom_x[11];
   out_8327048500586505475[12] = delta_x[12] + nom_x[12];
   out_8327048500586505475[13] = delta_x[13] + nom_x[13];
   out_8327048500586505475[14] = delta_x[14] + nom_x[14];
   out_8327048500586505475[15] = delta_x[15] + nom_x[15];
   out_8327048500586505475[16] = delta_x[16] + nom_x[16];
   out_8327048500586505475[17] = delta_x[17] + nom_x[17];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_1345819323802691490) {
   out_1345819323802691490[0] = -nom_x[0] + true_x[0];
   out_1345819323802691490[1] = -nom_x[1] + true_x[1];
   out_1345819323802691490[2] = -nom_x[2] + true_x[2];
   out_1345819323802691490[3] = -nom_x[3] + true_x[3];
   out_1345819323802691490[4] = -nom_x[4] + true_x[4];
   out_1345819323802691490[5] = -nom_x[5] + true_x[5];
   out_1345819323802691490[6] = -nom_x[6] + true_x[6];
   out_1345819323802691490[7] = -nom_x[7] + true_x[7];
   out_1345819323802691490[8] = -nom_x[8] + true_x[8];
   out_1345819323802691490[9] = -nom_x[9] + true_x[9];
   out_1345819323802691490[10] = -nom_x[10] + true_x[10];
   out_1345819323802691490[11] = -nom_x[11] + true_x[11];
   out_1345819323802691490[12] = -nom_x[12] + true_x[12];
   out_1345819323802691490[13] = -nom_x[13] + true_x[13];
   out_1345819323802691490[14] = -nom_x[14] + true_x[14];
   out_1345819323802691490[15] = -nom_x[15] + true_x[15];
   out_1345819323802691490[16] = -nom_x[16] + true_x[16];
   out_1345819323802691490[17] = -nom_x[17] + true_x[17];
}
void H_mod_fun(double *state, double *out_8287360551876046332) {
   out_8287360551876046332[0] = 1.0;
   out_8287360551876046332[1] = 0.0;
   out_8287360551876046332[2] = 0.0;
   out_8287360551876046332[3] = 0.0;
   out_8287360551876046332[4] = 0.0;
   out_8287360551876046332[5] = 0.0;
   out_8287360551876046332[6] = 0.0;
   out_8287360551876046332[7] = 0.0;
   out_8287360551876046332[8] = 0.0;
   out_8287360551876046332[9] = 0.0;
   out_8287360551876046332[10] = 0.0;
   out_8287360551876046332[11] = 0.0;
   out_8287360551876046332[12] = 0.0;
   out_8287360551876046332[13] = 0.0;
   out_8287360551876046332[14] = 0.0;
   out_8287360551876046332[15] = 0.0;
   out_8287360551876046332[16] = 0.0;
   out_8287360551876046332[17] = 0.0;
   out_8287360551876046332[18] = 0.0;
   out_8287360551876046332[19] = 1.0;
   out_8287360551876046332[20] = 0.0;
   out_8287360551876046332[21] = 0.0;
   out_8287360551876046332[22] = 0.0;
   out_8287360551876046332[23] = 0.0;
   out_8287360551876046332[24] = 0.0;
   out_8287360551876046332[25] = 0.0;
   out_8287360551876046332[26] = 0.0;
   out_8287360551876046332[27] = 0.0;
   out_8287360551876046332[28] = 0.0;
   out_8287360551876046332[29] = 0.0;
   out_8287360551876046332[30] = 0.0;
   out_8287360551876046332[31] = 0.0;
   out_8287360551876046332[32] = 0.0;
   out_8287360551876046332[33] = 0.0;
   out_8287360551876046332[34] = 0.0;
   out_8287360551876046332[35] = 0.0;
   out_8287360551876046332[36] = 0.0;
   out_8287360551876046332[37] = 0.0;
   out_8287360551876046332[38] = 1.0;
   out_8287360551876046332[39] = 0.0;
   out_8287360551876046332[40] = 0.0;
   out_8287360551876046332[41] = 0.0;
   out_8287360551876046332[42] = 0.0;
   out_8287360551876046332[43] = 0.0;
   out_8287360551876046332[44] = 0.0;
   out_8287360551876046332[45] = 0.0;
   out_8287360551876046332[46] = 0.0;
   out_8287360551876046332[47] = 0.0;
   out_8287360551876046332[48] = 0.0;
   out_8287360551876046332[49] = 0.0;
   out_8287360551876046332[50] = 0.0;
   out_8287360551876046332[51] = 0.0;
   out_8287360551876046332[52] = 0.0;
   out_8287360551876046332[53] = 0.0;
   out_8287360551876046332[54] = 0.0;
   out_8287360551876046332[55] = 0.0;
   out_8287360551876046332[56] = 0.0;
   out_8287360551876046332[57] = 1.0;
   out_8287360551876046332[58] = 0.0;
   out_8287360551876046332[59] = 0.0;
   out_8287360551876046332[60] = 0.0;
   out_8287360551876046332[61] = 0.0;
   out_8287360551876046332[62] = 0.0;
   out_8287360551876046332[63] = 0.0;
   out_8287360551876046332[64] = 0.0;
   out_8287360551876046332[65] = 0.0;
   out_8287360551876046332[66] = 0.0;
   out_8287360551876046332[67] = 0.0;
   out_8287360551876046332[68] = 0.0;
   out_8287360551876046332[69] = 0.0;
   out_8287360551876046332[70] = 0.0;
   out_8287360551876046332[71] = 0.0;
   out_8287360551876046332[72] = 0.0;
   out_8287360551876046332[73] = 0.0;
   out_8287360551876046332[74] = 0.0;
   out_8287360551876046332[75] = 0.0;
   out_8287360551876046332[76] = 1.0;
   out_8287360551876046332[77] = 0.0;
   out_8287360551876046332[78] = 0.0;
   out_8287360551876046332[79] = 0.0;
   out_8287360551876046332[80] = 0.0;
   out_8287360551876046332[81] = 0.0;
   out_8287360551876046332[82] = 0.0;
   out_8287360551876046332[83] = 0.0;
   out_8287360551876046332[84] = 0.0;
   out_8287360551876046332[85] = 0.0;
   out_8287360551876046332[86] = 0.0;
   out_8287360551876046332[87] = 0.0;
   out_8287360551876046332[88] = 0.0;
   out_8287360551876046332[89] = 0.0;
   out_8287360551876046332[90] = 0.0;
   out_8287360551876046332[91] = 0.0;
   out_8287360551876046332[92] = 0.0;
   out_8287360551876046332[93] = 0.0;
   out_8287360551876046332[94] = 0.0;
   out_8287360551876046332[95] = 1.0;
   out_8287360551876046332[96] = 0.0;
   out_8287360551876046332[97] = 0.0;
   out_8287360551876046332[98] = 0.0;
   out_8287360551876046332[99] = 0.0;
   out_8287360551876046332[100] = 0.0;
   out_8287360551876046332[101] = 0.0;
   out_8287360551876046332[102] = 0.0;
   out_8287360551876046332[103] = 0.0;
   out_8287360551876046332[104] = 0.0;
   out_8287360551876046332[105] = 0.0;
   out_8287360551876046332[106] = 0.0;
   out_8287360551876046332[107] = 0.0;
   out_8287360551876046332[108] = 0.0;
   out_8287360551876046332[109] = 0.0;
   out_8287360551876046332[110] = 0.0;
   out_8287360551876046332[111] = 0.0;
   out_8287360551876046332[112] = 0.0;
   out_8287360551876046332[113] = 0.0;
   out_8287360551876046332[114] = 1.0;
   out_8287360551876046332[115] = 0.0;
   out_8287360551876046332[116] = 0.0;
   out_8287360551876046332[117] = 0.0;
   out_8287360551876046332[118] = 0.0;
   out_8287360551876046332[119] = 0.0;
   out_8287360551876046332[120] = 0.0;
   out_8287360551876046332[121] = 0.0;
   out_8287360551876046332[122] = 0.0;
   out_8287360551876046332[123] = 0.0;
   out_8287360551876046332[124] = 0.0;
   out_8287360551876046332[125] = 0.0;
   out_8287360551876046332[126] = 0.0;
   out_8287360551876046332[127] = 0.0;
   out_8287360551876046332[128] = 0.0;
   out_8287360551876046332[129] = 0.0;
   out_8287360551876046332[130] = 0.0;
   out_8287360551876046332[131] = 0.0;
   out_8287360551876046332[132] = 0.0;
   out_8287360551876046332[133] = 1.0;
   out_8287360551876046332[134] = 0.0;
   out_8287360551876046332[135] = 0.0;
   out_8287360551876046332[136] = 0.0;
   out_8287360551876046332[137] = 0.0;
   out_8287360551876046332[138] = 0.0;
   out_8287360551876046332[139] = 0.0;
   out_8287360551876046332[140] = 0.0;
   out_8287360551876046332[141] = 0.0;
   out_8287360551876046332[142] = 0.0;
   out_8287360551876046332[143] = 0.0;
   out_8287360551876046332[144] = 0.0;
   out_8287360551876046332[145] = 0.0;
   out_8287360551876046332[146] = 0.0;
   out_8287360551876046332[147] = 0.0;
   out_8287360551876046332[148] = 0.0;
   out_8287360551876046332[149] = 0.0;
   out_8287360551876046332[150] = 0.0;
   out_8287360551876046332[151] = 0.0;
   out_8287360551876046332[152] = 1.0;
   out_8287360551876046332[153] = 0.0;
   out_8287360551876046332[154] = 0.0;
   out_8287360551876046332[155] = 0.0;
   out_8287360551876046332[156] = 0.0;
   out_8287360551876046332[157] = 0.0;
   out_8287360551876046332[158] = 0.0;
   out_8287360551876046332[159] = 0.0;
   out_8287360551876046332[160] = 0.0;
   out_8287360551876046332[161] = 0.0;
   out_8287360551876046332[162] = 0.0;
   out_8287360551876046332[163] = 0.0;
   out_8287360551876046332[164] = 0.0;
   out_8287360551876046332[165] = 0.0;
   out_8287360551876046332[166] = 0.0;
   out_8287360551876046332[167] = 0.0;
   out_8287360551876046332[168] = 0.0;
   out_8287360551876046332[169] = 0.0;
   out_8287360551876046332[170] = 0.0;
   out_8287360551876046332[171] = 1.0;
   out_8287360551876046332[172] = 0.0;
   out_8287360551876046332[173] = 0.0;
   out_8287360551876046332[174] = 0.0;
   out_8287360551876046332[175] = 0.0;
   out_8287360551876046332[176] = 0.0;
   out_8287360551876046332[177] = 0.0;
   out_8287360551876046332[178] = 0.0;
   out_8287360551876046332[179] = 0.0;
   out_8287360551876046332[180] = 0.0;
   out_8287360551876046332[181] = 0.0;
   out_8287360551876046332[182] = 0.0;
   out_8287360551876046332[183] = 0.0;
   out_8287360551876046332[184] = 0.0;
   out_8287360551876046332[185] = 0.0;
   out_8287360551876046332[186] = 0.0;
   out_8287360551876046332[187] = 0.0;
   out_8287360551876046332[188] = 0.0;
   out_8287360551876046332[189] = 0.0;
   out_8287360551876046332[190] = 1.0;
   out_8287360551876046332[191] = 0.0;
   out_8287360551876046332[192] = 0.0;
   out_8287360551876046332[193] = 0.0;
   out_8287360551876046332[194] = 0.0;
   out_8287360551876046332[195] = 0.0;
   out_8287360551876046332[196] = 0.0;
   out_8287360551876046332[197] = 0.0;
   out_8287360551876046332[198] = 0.0;
   out_8287360551876046332[199] = 0.0;
   out_8287360551876046332[200] = 0.0;
   out_8287360551876046332[201] = 0.0;
   out_8287360551876046332[202] = 0.0;
   out_8287360551876046332[203] = 0.0;
   out_8287360551876046332[204] = 0.0;
   out_8287360551876046332[205] = 0.0;
   out_8287360551876046332[206] = 0.0;
   out_8287360551876046332[207] = 0.0;
   out_8287360551876046332[208] = 0.0;
   out_8287360551876046332[209] = 1.0;
   out_8287360551876046332[210] = 0.0;
   out_8287360551876046332[211] = 0.0;
   out_8287360551876046332[212] = 0.0;
   out_8287360551876046332[213] = 0.0;
   out_8287360551876046332[214] = 0.0;
   out_8287360551876046332[215] = 0.0;
   out_8287360551876046332[216] = 0.0;
   out_8287360551876046332[217] = 0.0;
   out_8287360551876046332[218] = 0.0;
   out_8287360551876046332[219] = 0.0;
   out_8287360551876046332[220] = 0.0;
   out_8287360551876046332[221] = 0.0;
   out_8287360551876046332[222] = 0.0;
   out_8287360551876046332[223] = 0.0;
   out_8287360551876046332[224] = 0.0;
   out_8287360551876046332[225] = 0.0;
   out_8287360551876046332[226] = 0.0;
   out_8287360551876046332[227] = 0.0;
   out_8287360551876046332[228] = 1.0;
   out_8287360551876046332[229] = 0.0;
   out_8287360551876046332[230] = 0.0;
   out_8287360551876046332[231] = 0.0;
   out_8287360551876046332[232] = 0.0;
   out_8287360551876046332[233] = 0.0;
   out_8287360551876046332[234] = 0.0;
   out_8287360551876046332[235] = 0.0;
   out_8287360551876046332[236] = 0.0;
   out_8287360551876046332[237] = 0.0;
   out_8287360551876046332[238] = 0.0;
   out_8287360551876046332[239] = 0.0;
   out_8287360551876046332[240] = 0.0;
   out_8287360551876046332[241] = 0.0;
   out_8287360551876046332[242] = 0.0;
   out_8287360551876046332[243] = 0.0;
   out_8287360551876046332[244] = 0.0;
   out_8287360551876046332[245] = 0.0;
   out_8287360551876046332[246] = 0.0;
   out_8287360551876046332[247] = 1.0;
   out_8287360551876046332[248] = 0.0;
   out_8287360551876046332[249] = 0.0;
   out_8287360551876046332[250] = 0.0;
   out_8287360551876046332[251] = 0.0;
   out_8287360551876046332[252] = 0.0;
   out_8287360551876046332[253] = 0.0;
   out_8287360551876046332[254] = 0.0;
   out_8287360551876046332[255] = 0.0;
   out_8287360551876046332[256] = 0.0;
   out_8287360551876046332[257] = 0.0;
   out_8287360551876046332[258] = 0.0;
   out_8287360551876046332[259] = 0.0;
   out_8287360551876046332[260] = 0.0;
   out_8287360551876046332[261] = 0.0;
   out_8287360551876046332[262] = 0.0;
   out_8287360551876046332[263] = 0.0;
   out_8287360551876046332[264] = 0.0;
   out_8287360551876046332[265] = 0.0;
   out_8287360551876046332[266] = 1.0;
   out_8287360551876046332[267] = 0.0;
   out_8287360551876046332[268] = 0.0;
   out_8287360551876046332[269] = 0.0;
   out_8287360551876046332[270] = 0.0;
   out_8287360551876046332[271] = 0.0;
   out_8287360551876046332[272] = 0.0;
   out_8287360551876046332[273] = 0.0;
   out_8287360551876046332[274] = 0.0;
   out_8287360551876046332[275] = 0.0;
   out_8287360551876046332[276] = 0.0;
   out_8287360551876046332[277] = 0.0;
   out_8287360551876046332[278] = 0.0;
   out_8287360551876046332[279] = 0.0;
   out_8287360551876046332[280] = 0.0;
   out_8287360551876046332[281] = 0.0;
   out_8287360551876046332[282] = 0.0;
   out_8287360551876046332[283] = 0.0;
   out_8287360551876046332[284] = 0.0;
   out_8287360551876046332[285] = 1.0;
   out_8287360551876046332[286] = 0.0;
   out_8287360551876046332[287] = 0.0;
   out_8287360551876046332[288] = 0.0;
   out_8287360551876046332[289] = 0.0;
   out_8287360551876046332[290] = 0.0;
   out_8287360551876046332[291] = 0.0;
   out_8287360551876046332[292] = 0.0;
   out_8287360551876046332[293] = 0.0;
   out_8287360551876046332[294] = 0.0;
   out_8287360551876046332[295] = 0.0;
   out_8287360551876046332[296] = 0.0;
   out_8287360551876046332[297] = 0.0;
   out_8287360551876046332[298] = 0.0;
   out_8287360551876046332[299] = 0.0;
   out_8287360551876046332[300] = 0.0;
   out_8287360551876046332[301] = 0.0;
   out_8287360551876046332[302] = 0.0;
   out_8287360551876046332[303] = 0.0;
   out_8287360551876046332[304] = 1.0;
   out_8287360551876046332[305] = 0.0;
   out_8287360551876046332[306] = 0.0;
   out_8287360551876046332[307] = 0.0;
   out_8287360551876046332[308] = 0.0;
   out_8287360551876046332[309] = 0.0;
   out_8287360551876046332[310] = 0.0;
   out_8287360551876046332[311] = 0.0;
   out_8287360551876046332[312] = 0.0;
   out_8287360551876046332[313] = 0.0;
   out_8287360551876046332[314] = 0.0;
   out_8287360551876046332[315] = 0.0;
   out_8287360551876046332[316] = 0.0;
   out_8287360551876046332[317] = 0.0;
   out_8287360551876046332[318] = 0.0;
   out_8287360551876046332[319] = 0.0;
   out_8287360551876046332[320] = 0.0;
   out_8287360551876046332[321] = 0.0;
   out_8287360551876046332[322] = 0.0;
   out_8287360551876046332[323] = 1.0;
}
void f_fun(double *state, double dt, double *out_76477989752059892) {
   out_76477989752059892[0] = atan2((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), -(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]));
   out_76477989752059892[1] = asin(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]));
   out_76477989752059892[2] = atan2(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), -(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]));
   out_76477989752059892[3] = dt*state[12] + state[3];
   out_76477989752059892[4] = dt*state[13] + state[4];
   out_76477989752059892[5] = dt*state[14] + state[5];
   out_76477989752059892[6] = state[6];
   out_76477989752059892[7] = state[7];
   out_76477989752059892[8] = state[8];
   out_76477989752059892[9] = state[9];
   out_76477989752059892[10] = state[10];
   out_76477989752059892[11] = state[11];
   out_76477989752059892[12] = state[12];
   out_76477989752059892[13] = state[13];
   out_76477989752059892[14] = state[14];
   out_76477989752059892[15] = state[15];
   out_76477989752059892[16] = state[16];
   out_76477989752059892[17] = state[17];
}
void F_fun(double *state, double dt, double *out_2587667055193245078) {
   out_2587667055193245078[0] = ((-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*cos(state[0])*cos(state[1]) - sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*cos(state[0])*cos(state[1]) - sin(dt*state[6])*sin(state[0])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_2587667055193245078[1] = ((-sin(dt*state[6])*sin(dt*state[8]) - sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*cos(state[1]) - (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*sin(state[1]) - sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(state[0]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*sin(state[1]) + (-sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) + sin(dt*state[8])*cos(dt*state[6]))*cos(state[1]) - sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(state[0]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_2587667055193245078[2] = 0;
   out_2587667055193245078[3] = 0;
   out_2587667055193245078[4] = 0;
   out_2587667055193245078[5] = 0;
   out_2587667055193245078[6] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(dt*cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) - dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_2587667055193245078[7] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*sin(dt*state[7])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[6])*sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) - dt*sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[7])*cos(dt*state[6])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[8])*sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]) - dt*sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_2587667055193245078[8] = ((dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((dt*sin(dt*state[6])*sin(dt*state[8]) + dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_2587667055193245078[9] = 0;
   out_2587667055193245078[10] = 0;
   out_2587667055193245078[11] = 0;
   out_2587667055193245078[12] = 0;
   out_2587667055193245078[13] = 0;
   out_2587667055193245078[14] = 0;
   out_2587667055193245078[15] = 0;
   out_2587667055193245078[16] = 0;
   out_2587667055193245078[17] = 0;
   out_2587667055193245078[18] = (-sin(dt*state[7])*sin(state[0])*cos(state[1]) - sin(dt*state[8])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_2587667055193245078[19] = (-sin(dt*state[7])*sin(state[1])*cos(state[0]) + sin(dt*state[8])*sin(state[0])*sin(state[1])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_2587667055193245078[20] = 0;
   out_2587667055193245078[21] = 0;
   out_2587667055193245078[22] = 0;
   out_2587667055193245078[23] = 0;
   out_2587667055193245078[24] = 0;
   out_2587667055193245078[25] = (dt*sin(dt*state[7])*sin(dt*state[8])*sin(state[0])*cos(state[1]) - dt*sin(dt*state[7])*sin(state[1])*cos(dt*state[8]) + dt*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_2587667055193245078[26] = (-dt*sin(dt*state[8])*sin(state[1])*cos(dt*state[7]) - dt*sin(state[0])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_2587667055193245078[27] = 0;
   out_2587667055193245078[28] = 0;
   out_2587667055193245078[29] = 0;
   out_2587667055193245078[30] = 0;
   out_2587667055193245078[31] = 0;
   out_2587667055193245078[32] = 0;
   out_2587667055193245078[33] = 0;
   out_2587667055193245078[34] = 0;
   out_2587667055193245078[35] = 0;
   out_2587667055193245078[36] = ((sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_2587667055193245078[37] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-sin(dt*state[7])*sin(state[2])*cos(state[0])*cos(state[1]) + sin(dt*state[8])*sin(state[0])*sin(state[2])*cos(dt*state[7])*cos(state[1]) - sin(state[1])*sin(state[2])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(-sin(dt*state[7])*cos(state[0])*cos(state[1])*cos(state[2]) + sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1])*cos(state[2]) - sin(state[1])*cos(dt*state[7])*cos(dt*state[8])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_2587667055193245078[38] = ((-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (-sin(state[0])*sin(state[1])*sin(state[2]) - cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_2587667055193245078[39] = 0;
   out_2587667055193245078[40] = 0;
   out_2587667055193245078[41] = 0;
   out_2587667055193245078[42] = 0;
   out_2587667055193245078[43] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(dt*(sin(state[0])*cos(state[2]) - sin(state[1])*sin(state[2])*cos(state[0]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*sin(state[2])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(dt*(-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_2587667055193245078[44] = (dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*sin(state[2])*cos(dt*state[7])*cos(state[1]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + (dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[7])*cos(state[1])*cos(state[2]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_2587667055193245078[45] = 0;
   out_2587667055193245078[46] = 0;
   out_2587667055193245078[47] = 0;
   out_2587667055193245078[48] = 0;
   out_2587667055193245078[49] = 0;
   out_2587667055193245078[50] = 0;
   out_2587667055193245078[51] = 0;
   out_2587667055193245078[52] = 0;
   out_2587667055193245078[53] = 0;
   out_2587667055193245078[54] = 0;
   out_2587667055193245078[55] = 0;
   out_2587667055193245078[56] = 0;
   out_2587667055193245078[57] = 1;
   out_2587667055193245078[58] = 0;
   out_2587667055193245078[59] = 0;
   out_2587667055193245078[60] = 0;
   out_2587667055193245078[61] = 0;
   out_2587667055193245078[62] = 0;
   out_2587667055193245078[63] = 0;
   out_2587667055193245078[64] = 0;
   out_2587667055193245078[65] = 0;
   out_2587667055193245078[66] = dt;
   out_2587667055193245078[67] = 0;
   out_2587667055193245078[68] = 0;
   out_2587667055193245078[69] = 0;
   out_2587667055193245078[70] = 0;
   out_2587667055193245078[71] = 0;
   out_2587667055193245078[72] = 0;
   out_2587667055193245078[73] = 0;
   out_2587667055193245078[74] = 0;
   out_2587667055193245078[75] = 0;
   out_2587667055193245078[76] = 1;
   out_2587667055193245078[77] = 0;
   out_2587667055193245078[78] = 0;
   out_2587667055193245078[79] = 0;
   out_2587667055193245078[80] = 0;
   out_2587667055193245078[81] = 0;
   out_2587667055193245078[82] = 0;
   out_2587667055193245078[83] = 0;
   out_2587667055193245078[84] = 0;
   out_2587667055193245078[85] = dt;
   out_2587667055193245078[86] = 0;
   out_2587667055193245078[87] = 0;
   out_2587667055193245078[88] = 0;
   out_2587667055193245078[89] = 0;
   out_2587667055193245078[90] = 0;
   out_2587667055193245078[91] = 0;
   out_2587667055193245078[92] = 0;
   out_2587667055193245078[93] = 0;
   out_2587667055193245078[94] = 0;
   out_2587667055193245078[95] = 1;
   out_2587667055193245078[96] = 0;
   out_2587667055193245078[97] = 0;
   out_2587667055193245078[98] = 0;
   out_2587667055193245078[99] = 0;
   out_2587667055193245078[100] = 0;
   out_2587667055193245078[101] = 0;
   out_2587667055193245078[102] = 0;
   out_2587667055193245078[103] = 0;
   out_2587667055193245078[104] = dt;
   out_2587667055193245078[105] = 0;
   out_2587667055193245078[106] = 0;
   out_2587667055193245078[107] = 0;
   out_2587667055193245078[108] = 0;
   out_2587667055193245078[109] = 0;
   out_2587667055193245078[110] = 0;
   out_2587667055193245078[111] = 0;
   out_2587667055193245078[112] = 0;
   out_2587667055193245078[113] = 0;
   out_2587667055193245078[114] = 1;
   out_2587667055193245078[115] = 0;
   out_2587667055193245078[116] = 0;
   out_2587667055193245078[117] = 0;
   out_2587667055193245078[118] = 0;
   out_2587667055193245078[119] = 0;
   out_2587667055193245078[120] = 0;
   out_2587667055193245078[121] = 0;
   out_2587667055193245078[122] = 0;
   out_2587667055193245078[123] = 0;
   out_2587667055193245078[124] = 0;
   out_2587667055193245078[125] = 0;
   out_2587667055193245078[126] = 0;
   out_2587667055193245078[127] = 0;
   out_2587667055193245078[128] = 0;
   out_2587667055193245078[129] = 0;
   out_2587667055193245078[130] = 0;
   out_2587667055193245078[131] = 0;
   out_2587667055193245078[132] = 0;
   out_2587667055193245078[133] = 1;
   out_2587667055193245078[134] = 0;
   out_2587667055193245078[135] = 0;
   out_2587667055193245078[136] = 0;
   out_2587667055193245078[137] = 0;
   out_2587667055193245078[138] = 0;
   out_2587667055193245078[139] = 0;
   out_2587667055193245078[140] = 0;
   out_2587667055193245078[141] = 0;
   out_2587667055193245078[142] = 0;
   out_2587667055193245078[143] = 0;
   out_2587667055193245078[144] = 0;
   out_2587667055193245078[145] = 0;
   out_2587667055193245078[146] = 0;
   out_2587667055193245078[147] = 0;
   out_2587667055193245078[148] = 0;
   out_2587667055193245078[149] = 0;
   out_2587667055193245078[150] = 0;
   out_2587667055193245078[151] = 0;
   out_2587667055193245078[152] = 1;
   out_2587667055193245078[153] = 0;
   out_2587667055193245078[154] = 0;
   out_2587667055193245078[155] = 0;
   out_2587667055193245078[156] = 0;
   out_2587667055193245078[157] = 0;
   out_2587667055193245078[158] = 0;
   out_2587667055193245078[159] = 0;
   out_2587667055193245078[160] = 0;
   out_2587667055193245078[161] = 0;
   out_2587667055193245078[162] = 0;
   out_2587667055193245078[163] = 0;
   out_2587667055193245078[164] = 0;
   out_2587667055193245078[165] = 0;
   out_2587667055193245078[166] = 0;
   out_2587667055193245078[167] = 0;
   out_2587667055193245078[168] = 0;
   out_2587667055193245078[169] = 0;
   out_2587667055193245078[170] = 0;
   out_2587667055193245078[171] = 1;
   out_2587667055193245078[172] = 0;
   out_2587667055193245078[173] = 0;
   out_2587667055193245078[174] = 0;
   out_2587667055193245078[175] = 0;
   out_2587667055193245078[176] = 0;
   out_2587667055193245078[177] = 0;
   out_2587667055193245078[178] = 0;
   out_2587667055193245078[179] = 0;
   out_2587667055193245078[180] = 0;
   out_2587667055193245078[181] = 0;
   out_2587667055193245078[182] = 0;
   out_2587667055193245078[183] = 0;
   out_2587667055193245078[184] = 0;
   out_2587667055193245078[185] = 0;
   out_2587667055193245078[186] = 0;
   out_2587667055193245078[187] = 0;
   out_2587667055193245078[188] = 0;
   out_2587667055193245078[189] = 0;
   out_2587667055193245078[190] = 1;
   out_2587667055193245078[191] = 0;
   out_2587667055193245078[192] = 0;
   out_2587667055193245078[193] = 0;
   out_2587667055193245078[194] = 0;
   out_2587667055193245078[195] = 0;
   out_2587667055193245078[196] = 0;
   out_2587667055193245078[197] = 0;
   out_2587667055193245078[198] = 0;
   out_2587667055193245078[199] = 0;
   out_2587667055193245078[200] = 0;
   out_2587667055193245078[201] = 0;
   out_2587667055193245078[202] = 0;
   out_2587667055193245078[203] = 0;
   out_2587667055193245078[204] = 0;
   out_2587667055193245078[205] = 0;
   out_2587667055193245078[206] = 0;
   out_2587667055193245078[207] = 0;
   out_2587667055193245078[208] = 0;
   out_2587667055193245078[209] = 1;
   out_2587667055193245078[210] = 0;
   out_2587667055193245078[211] = 0;
   out_2587667055193245078[212] = 0;
   out_2587667055193245078[213] = 0;
   out_2587667055193245078[214] = 0;
   out_2587667055193245078[215] = 0;
   out_2587667055193245078[216] = 0;
   out_2587667055193245078[217] = 0;
   out_2587667055193245078[218] = 0;
   out_2587667055193245078[219] = 0;
   out_2587667055193245078[220] = 0;
   out_2587667055193245078[221] = 0;
   out_2587667055193245078[222] = 0;
   out_2587667055193245078[223] = 0;
   out_2587667055193245078[224] = 0;
   out_2587667055193245078[225] = 0;
   out_2587667055193245078[226] = 0;
   out_2587667055193245078[227] = 0;
   out_2587667055193245078[228] = 1;
   out_2587667055193245078[229] = 0;
   out_2587667055193245078[230] = 0;
   out_2587667055193245078[231] = 0;
   out_2587667055193245078[232] = 0;
   out_2587667055193245078[233] = 0;
   out_2587667055193245078[234] = 0;
   out_2587667055193245078[235] = 0;
   out_2587667055193245078[236] = 0;
   out_2587667055193245078[237] = 0;
   out_2587667055193245078[238] = 0;
   out_2587667055193245078[239] = 0;
   out_2587667055193245078[240] = 0;
   out_2587667055193245078[241] = 0;
   out_2587667055193245078[242] = 0;
   out_2587667055193245078[243] = 0;
   out_2587667055193245078[244] = 0;
   out_2587667055193245078[245] = 0;
   out_2587667055193245078[246] = 0;
   out_2587667055193245078[247] = 1;
   out_2587667055193245078[248] = 0;
   out_2587667055193245078[249] = 0;
   out_2587667055193245078[250] = 0;
   out_2587667055193245078[251] = 0;
   out_2587667055193245078[252] = 0;
   out_2587667055193245078[253] = 0;
   out_2587667055193245078[254] = 0;
   out_2587667055193245078[255] = 0;
   out_2587667055193245078[256] = 0;
   out_2587667055193245078[257] = 0;
   out_2587667055193245078[258] = 0;
   out_2587667055193245078[259] = 0;
   out_2587667055193245078[260] = 0;
   out_2587667055193245078[261] = 0;
   out_2587667055193245078[262] = 0;
   out_2587667055193245078[263] = 0;
   out_2587667055193245078[264] = 0;
   out_2587667055193245078[265] = 0;
   out_2587667055193245078[266] = 1;
   out_2587667055193245078[267] = 0;
   out_2587667055193245078[268] = 0;
   out_2587667055193245078[269] = 0;
   out_2587667055193245078[270] = 0;
   out_2587667055193245078[271] = 0;
   out_2587667055193245078[272] = 0;
   out_2587667055193245078[273] = 0;
   out_2587667055193245078[274] = 0;
   out_2587667055193245078[275] = 0;
   out_2587667055193245078[276] = 0;
   out_2587667055193245078[277] = 0;
   out_2587667055193245078[278] = 0;
   out_2587667055193245078[279] = 0;
   out_2587667055193245078[280] = 0;
   out_2587667055193245078[281] = 0;
   out_2587667055193245078[282] = 0;
   out_2587667055193245078[283] = 0;
   out_2587667055193245078[284] = 0;
   out_2587667055193245078[285] = 1;
   out_2587667055193245078[286] = 0;
   out_2587667055193245078[287] = 0;
   out_2587667055193245078[288] = 0;
   out_2587667055193245078[289] = 0;
   out_2587667055193245078[290] = 0;
   out_2587667055193245078[291] = 0;
   out_2587667055193245078[292] = 0;
   out_2587667055193245078[293] = 0;
   out_2587667055193245078[294] = 0;
   out_2587667055193245078[295] = 0;
   out_2587667055193245078[296] = 0;
   out_2587667055193245078[297] = 0;
   out_2587667055193245078[298] = 0;
   out_2587667055193245078[299] = 0;
   out_2587667055193245078[300] = 0;
   out_2587667055193245078[301] = 0;
   out_2587667055193245078[302] = 0;
   out_2587667055193245078[303] = 0;
   out_2587667055193245078[304] = 1;
   out_2587667055193245078[305] = 0;
   out_2587667055193245078[306] = 0;
   out_2587667055193245078[307] = 0;
   out_2587667055193245078[308] = 0;
   out_2587667055193245078[309] = 0;
   out_2587667055193245078[310] = 0;
   out_2587667055193245078[311] = 0;
   out_2587667055193245078[312] = 0;
   out_2587667055193245078[313] = 0;
   out_2587667055193245078[314] = 0;
   out_2587667055193245078[315] = 0;
   out_2587667055193245078[316] = 0;
   out_2587667055193245078[317] = 0;
   out_2587667055193245078[318] = 0;
   out_2587667055193245078[319] = 0;
   out_2587667055193245078[320] = 0;
   out_2587667055193245078[321] = 0;
   out_2587667055193245078[322] = 0;
   out_2587667055193245078[323] = 1;
}
void h_4(double *state, double *unused, double *out_8356936087827293267) {
   out_8356936087827293267[0] = state[6] + state[9];
   out_8356936087827293267[1] = state[7] + state[10];
   out_8356936087827293267[2] = state[8] + state[11];
}
void H_4(double *state, double *unused, double *out_117195959047770632) {
   out_117195959047770632[0] = 0;
   out_117195959047770632[1] = 0;
   out_117195959047770632[2] = 0;
   out_117195959047770632[3] = 0;
   out_117195959047770632[4] = 0;
   out_117195959047770632[5] = 0;
   out_117195959047770632[6] = 1;
   out_117195959047770632[7] = 0;
   out_117195959047770632[8] = 0;
   out_117195959047770632[9] = 1;
   out_117195959047770632[10] = 0;
   out_117195959047770632[11] = 0;
   out_117195959047770632[12] = 0;
   out_117195959047770632[13] = 0;
   out_117195959047770632[14] = 0;
   out_117195959047770632[15] = 0;
   out_117195959047770632[16] = 0;
   out_117195959047770632[17] = 0;
   out_117195959047770632[18] = 0;
   out_117195959047770632[19] = 0;
   out_117195959047770632[20] = 0;
   out_117195959047770632[21] = 0;
   out_117195959047770632[22] = 0;
   out_117195959047770632[23] = 0;
   out_117195959047770632[24] = 0;
   out_117195959047770632[25] = 1;
   out_117195959047770632[26] = 0;
   out_117195959047770632[27] = 0;
   out_117195959047770632[28] = 1;
   out_117195959047770632[29] = 0;
   out_117195959047770632[30] = 0;
   out_117195959047770632[31] = 0;
   out_117195959047770632[32] = 0;
   out_117195959047770632[33] = 0;
   out_117195959047770632[34] = 0;
   out_117195959047770632[35] = 0;
   out_117195959047770632[36] = 0;
   out_117195959047770632[37] = 0;
   out_117195959047770632[38] = 0;
   out_117195959047770632[39] = 0;
   out_117195959047770632[40] = 0;
   out_117195959047770632[41] = 0;
   out_117195959047770632[42] = 0;
   out_117195959047770632[43] = 0;
   out_117195959047770632[44] = 1;
   out_117195959047770632[45] = 0;
   out_117195959047770632[46] = 0;
   out_117195959047770632[47] = 1;
   out_117195959047770632[48] = 0;
   out_117195959047770632[49] = 0;
   out_117195959047770632[50] = 0;
   out_117195959047770632[51] = 0;
   out_117195959047770632[52] = 0;
   out_117195959047770632[53] = 0;
}
void h_10(double *state, double *unused, double *out_4187746716742178647) {
   out_4187746716742178647[0] = 9.8100000000000005*sin(state[1]) - state[4]*state[8] + state[5]*state[7] + state[12] + state[15];
   out_4187746716742178647[1] = -9.8100000000000005*sin(state[0])*cos(state[1]) + state[3]*state[8] - state[5]*state[6] + state[13] + state[16];
   out_4187746716742178647[2] = -9.8100000000000005*cos(state[0])*cos(state[1]) - state[3]*state[7] + state[4]*state[6] + state[14] + state[17];
}
void H_10(double *state, double *unused, double *out_4255482199594732963) {
   out_4255482199594732963[0] = 0;
   out_4255482199594732963[1] = 9.8100000000000005*cos(state[1]);
   out_4255482199594732963[2] = 0;
   out_4255482199594732963[3] = 0;
   out_4255482199594732963[4] = -state[8];
   out_4255482199594732963[5] = state[7];
   out_4255482199594732963[6] = 0;
   out_4255482199594732963[7] = state[5];
   out_4255482199594732963[8] = -state[4];
   out_4255482199594732963[9] = 0;
   out_4255482199594732963[10] = 0;
   out_4255482199594732963[11] = 0;
   out_4255482199594732963[12] = 1;
   out_4255482199594732963[13] = 0;
   out_4255482199594732963[14] = 0;
   out_4255482199594732963[15] = 1;
   out_4255482199594732963[16] = 0;
   out_4255482199594732963[17] = 0;
   out_4255482199594732963[18] = -9.8100000000000005*cos(state[0])*cos(state[1]);
   out_4255482199594732963[19] = 9.8100000000000005*sin(state[0])*sin(state[1]);
   out_4255482199594732963[20] = 0;
   out_4255482199594732963[21] = state[8];
   out_4255482199594732963[22] = 0;
   out_4255482199594732963[23] = -state[6];
   out_4255482199594732963[24] = -state[5];
   out_4255482199594732963[25] = 0;
   out_4255482199594732963[26] = state[3];
   out_4255482199594732963[27] = 0;
   out_4255482199594732963[28] = 0;
   out_4255482199594732963[29] = 0;
   out_4255482199594732963[30] = 0;
   out_4255482199594732963[31] = 1;
   out_4255482199594732963[32] = 0;
   out_4255482199594732963[33] = 0;
   out_4255482199594732963[34] = 1;
   out_4255482199594732963[35] = 0;
   out_4255482199594732963[36] = 9.8100000000000005*sin(state[0])*cos(state[1]);
   out_4255482199594732963[37] = 9.8100000000000005*sin(state[1])*cos(state[0]);
   out_4255482199594732963[38] = 0;
   out_4255482199594732963[39] = -state[7];
   out_4255482199594732963[40] = state[6];
   out_4255482199594732963[41] = 0;
   out_4255482199594732963[42] = state[4];
   out_4255482199594732963[43] = -state[3];
   out_4255482199594732963[44] = 0;
   out_4255482199594732963[45] = 0;
   out_4255482199594732963[46] = 0;
   out_4255482199594732963[47] = 0;
   out_4255482199594732963[48] = 0;
   out_4255482199594732963[49] = 0;
   out_4255482199594732963[50] = 1;
   out_4255482199594732963[51] = 0;
   out_4255482199594732963[52] = 0;
   out_4255482199594732963[53] = 1;
}
void h_13(double *state, double *unused, double *out_631883575165978985) {
   out_631883575165978985[0] = state[3];
   out_631883575165978985[1] = state[4];
   out_631883575165978985[2] = state[5];
}
void H_13(double *state, double *unused, double *out_3095077866284562169) {
   out_3095077866284562169[0] = 0;
   out_3095077866284562169[1] = 0;
   out_3095077866284562169[2] = 0;
   out_3095077866284562169[3] = 1;
   out_3095077866284562169[4] = 0;
   out_3095077866284562169[5] = 0;
   out_3095077866284562169[6] = 0;
   out_3095077866284562169[7] = 0;
   out_3095077866284562169[8] = 0;
   out_3095077866284562169[9] = 0;
   out_3095077866284562169[10] = 0;
   out_3095077866284562169[11] = 0;
   out_3095077866284562169[12] = 0;
   out_3095077866284562169[13] = 0;
   out_3095077866284562169[14] = 0;
   out_3095077866284562169[15] = 0;
   out_3095077866284562169[16] = 0;
   out_3095077866284562169[17] = 0;
   out_3095077866284562169[18] = 0;
   out_3095077866284562169[19] = 0;
   out_3095077866284562169[20] = 0;
   out_3095077866284562169[21] = 0;
   out_3095077866284562169[22] = 1;
   out_3095077866284562169[23] = 0;
   out_3095077866284562169[24] = 0;
   out_3095077866284562169[25] = 0;
   out_3095077866284562169[26] = 0;
   out_3095077866284562169[27] = 0;
   out_3095077866284562169[28] = 0;
   out_3095077866284562169[29] = 0;
   out_3095077866284562169[30] = 0;
   out_3095077866284562169[31] = 0;
   out_3095077866284562169[32] = 0;
   out_3095077866284562169[33] = 0;
   out_3095077866284562169[34] = 0;
   out_3095077866284562169[35] = 0;
   out_3095077866284562169[36] = 0;
   out_3095077866284562169[37] = 0;
   out_3095077866284562169[38] = 0;
   out_3095077866284562169[39] = 0;
   out_3095077866284562169[40] = 0;
   out_3095077866284562169[41] = 1;
   out_3095077866284562169[42] = 0;
   out_3095077866284562169[43] = 0;
   out_3095077866284562169[44] = 0;
   out_3095077866284562169[45] = 0;
   out_3095077866284562169[46] = 0;
   out_3095077866284562169[47] = 0;
   out_3095077866284562169[48] = 0;
   out_3095077866284562169[49] = 0;
   out_3095077866284562169[50] = 0;
   out_3095077866284562169[51] = 0;
   out_3095077866284562169[52] = 0;
   out_3095077866284562169[53] = 0;
}
void h_14(double *state, double *unused, double *out_6652898583954639418) {
   out_6652898583954639418[0] = state[6];
   out_6652898583954639418[1] = state[7];
   out_6652898583954639418[2] = state[8];
}
void H_14(double *state, double *unused, double *out_552312485692654231) {
   out_552312485692654231[0] = 0;
   out_552312485692654231[1] = 0;
   out_552312485692654231[2] = 0;
   out_552312485692654231[3] = 0;
   out_552312485692654231[4] = 0;
   out_552312485692654231[5] = 0;
   out_552312485692654231[6] = 1;
   out_552312485692654231[7] = 0;
   out_552312485692654231[8] = 0;
   out_552312485692654231[9] = 0;
   out_552312485692654231[10] = 0;
   out_552312485692654231[11] = 0;
   out_552312485692654231[12] = 0;
   out_552312485692654231[13] = 0;
   out_552312485692654231[14] = 0;
   out_552312485692654231[15] = 0;
   out_552312485692654231[16] = 0;
   out_552312485692654231[17] = 0;
   out_552312485692654231[18] = 0;
   out_552312485692654231[19] = 0;
   out_552312485692654231[20] = 0;
   out_552312485692654231[21] = 0;
   out_552312485692654231[22] = 0;
   out_552312485692654231[23] = 0;
   out_552312485692654231[24] = 0;
   out_552312485692654231[25] = 1;
   out_552312485692654231[26] = 0;
   out_552312485692654231[27] = 0;
   out_552312485692654231[28] = 0;
   out_552312485692654231[29] = 0;
   out_552312485692654231[30] = 0;
   out_552312485692654231[31] = 0;
   out_552312485692654231[32] = 0;
   out_552312485692654231[33] = 0;
   out_552312485692654231[34] = 0;
   out_552312485692654231[35] = 0;
   out_552312485692654231[36] = 0;
   out_552312485692654231[37] = 0;
   out_552312485692654231[38] = 0;
   out_552312485692654231[39] = 0;
   out_552312485692654231[40] = 0;
   out_552312485692654231[41] = 0;
   out_552312485692654231[42] = 0;
   out_552312485692654231[43] = 0;
   out_552312485692654231[44] = 1;
   out_552312485692654231[45] = 0;
   out_552312485692654231[46] = 0;
   out_552312485692654231[47] = 0;
   out_552312485692654231[48] = 0;
   out_552312485692654231[49] = 0;
   out_552312485692654231[50] = 0;
   out_552312485692654231[51] = 0;
   out_552312485692654231[52] = 0;
   out_552312485692654231[53] = 0;
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
void pose_err_fun(double *nom_x, double *delta_x, double *out_8327048500586505475) {
  err_fun(nom_x, delta_x, out_8327048500586505475);
}
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_1345819323802691490) {
  inv_err_fun(nom_x, true_x, out_1345819323802691490);
}
void pose_H_mod_fun(double *state, double *out_8287360551876046332) {
  H_mod_fun(state, out_8287360551876046332);
}
void pose_f_fun(double *state, double dt, double *out_76477989752059892) {
  f_fun(state,  dt, out_76477989752059892);
}
void pose_F_fun(double *state, double dt, double *out_2587667055193245078) {
  F_fun(state,  dt, out_2587667055193245078);
}
void pose_h_4(double *state, double *unused, double *out_8356936087827293267) {
  h_4(state, unused, out_8356936087827293267);
}
void pose_H_4(double *state, double *unused, double *out_117195959047770632) {
  H_4(state, unused, out_117195959047770632);
}
void pose_h_10(double *state, double *unused, double *out_4187746716742178647) {
  h_10(state, unused, out_4187746716742178647);
}
void pose_H_10(double *state, double *unused, double *out_4255482199594732963) {
  H_10(state, unused, out_4255482199594732963);
}
void pose_h_13(double *state, double *unused, double *out_631883575165978985) {
  h_13(state, unused, out_631883575165978985);
}
void pose_H_13(double *state, double *unused, double *out_3095077866284562169) {
  H_13(state, unused, out_3095077866284562169);
}
void pose_h_14(double *state, double *unused, double *out_6652898583954639418) {
  h_14(state, unused, out_6652898583954639418);
}
void pose_H_14(double *state, double *unused, double *out_552312485692654231) {
  H_14(state, unused, out_552312485692654231);
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
