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
void err_fun(double *nom_x, double *delta_x, double *out_7675941765646048454) {
   out_7675941765646048454[0] = delta_x[0] + nom_x[0];
   out_7675941765646048454[1] = delta_x[1] + nom_x[1];
   out_7675941765646048454[2] = delta_x[2] + nom_x[2];
   out_7675941765646048454[3] = delta_x[3] + nom_x[3];
   out_7675941765646048454[4] = delta_x[4] + nom_x[4];
   out_7675941765646048454[5] = delta_x[5] + nom_x[5];
   out_7675941765646048454[6] = delta_x[6] + nom_x[6];
   out_7675941765646048454[7] = delta_x[7] + nom_x[7];
   out_7675941765646048454[8] = delta_x[8] + nom_x[8];
   out_7675941765646048454[9] = delta_x[9] + nom_x[9];
   out_7675941765646048454[10] = delta_x[10] + nom_x[10];
   out_7675941765646048454[11] = delta_x[11] + nom_x[11];
   out_7675941765646048454[12] = delta_x[12] + nom_x[12];
   out_7675941765646048454[13] = delta_x[13] + nom_x[13];
   out_7675941765646048454[14] = delta_x[14] + nom_x[14];
   out_7675941765646048454[15] = delta_x[15] + nom_x[15];
   out_7675941765646048454[16] = delta_x[16] + nom_x[16];
   out_7675941765646048454[17] = delta_x[17] + nom_x[17];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_6578985106349638079) {
   out_6578985106349638079[0] = -nom_x[0] + true_x[0];
   out_6578985106349638079[1] = -nom_x[1] + true_x[1];
   out_6578985106349638079[2] = -nom_x[2] + true_x[2];
   out_6578985106349638079[3] = -nom_x[3] + true_x[3];
   out_6578985106349638079[4] = -nom_x[4] + true_x[4];
   out_6578985106349638079[5] = -nom_x[5] + true_x[5];
   out_6578985106349638079[6] = -nom_x[6] + true_x[6];
   out_6578985106349638079[7] = -nom_x[7] + true_x[7];
   out_6578985106349638079[8] = -nom_x[8] + true_x[8];
   out_6578985106349638079[9] = -nom_x[9] + true_x[9];
   out_6578985106349638079[10] = -nom_x[10] + true_x[10];
   out_6578985106349638079[11] = -nom_x[11] + true_x[11];
   out_6578985106349638079[12] = -nom_x[12] + true_x[12];
   out_6578985106349638079[13] = -nom_x[13] + true_x[13];
   out_6578985106349638079[14] = -nom_x[14] + true_x[14];
   out_6578985106349638079[15] = -nom_x[15] + true_x[15];
   out_6578985106349638079[16] = -nom_x[16] + true_x[16];
   out_6578985106349638079[17] = -nom_x[17] + true_x[17];
}
void H_mod_fun(double *state, double *out_8249219982215908455) {
   out_8249219982215908455[0] = 1.0;
   out_8249219982215908455[1] = 0.0;
   out_8249219982215908455[2] = 0.0;
   out_8249219982215908455[3] = 0.0;
   out_8249219982215908455[4] = 0.0;
   out_8249219982215908455[5] = 0.0;
   out_8249219982215908455[6] = 0.0;
   out_8249219982215908455[7] = 0.0;
   out_8249219982215908455[8] = 0.0;
   out_8249219982215908455[9] = 0.0;
   out_8249219982215908455[10] = 0.0;
   out_8249219982215908455[11] = 0.0;
   out_8249219982215908455[12] = 0.0;
   out_8249219982215908455[13] = 0.0;
   out_8249219982215908455[14] = 0.0;
   out_8249219982215908455[15] = 0.0;
   out_8249219982215908455[16] = 0.0;
   out_8249219982215908455[17] = 0.0;
   out_8249219982215908455[18] = 0.0;
   out_8249219982215908455[19] = 1.0;
   out_8249219982215908455[20] = 0.0;
   out_8249219982215908455[21] = 0.0;
   out_8249219982215908455[22] = 0.0;
   out_8249219982215908455[23] = 0.0;
   out_8249219982215908455[24] = 0.0;
   out_8249219982215908455[25] = 0.0;
   out_8249219982215908455[26] = 0.0;
   out_8249219982215908455[27] = 0.0;
   out_8249219982215908455[28] = 0.0;
   out_8249219982215908455[29] = 0.0;
   out_8249219982215908455[30] = 0.0;
   out_8249219982215908455[31] = 0.0;
   out_8249219982215908455[32] = 0.0;
   out_8249219982215908455[33] = 0.0;
   out_8249219982215908455[34] = 0.0;
   out_8249219982215908455[35] = 0.0;
   out_8249219982215908455[36] = 0.0;
   out_8249219982215908455[37] = 0.0;
   out_8249219982215908455[38] = 1.0;
   out_8249219982215908455[39] = 0.0;
   out_8249219982215908455[40] = 0.0;
   out_8249219982215908455[41] = 0.0;
   out_8249219982215908455[42] = 0.0;
   out_8249219982215908455[43] = 0.0;
   out_8249219982215908455[44] = 0.0;
   out_8249219982215908455[45] = 0.0;
   out_8249219982215908455[46] = 0.0;
   out_8249219982215908455[47] = 0.0;
   out_8249219982215908455[48] = 0.0;
   out_8249219982215908455[49] = 0.0;
   out_8249219982215908455[50] = 0.0;
   out_8249219982215908455[51] = 0.0;
   out_8249219982215908455[52] = 0.0;
   out_8249219982215908455[53] = 0.0;
   out_8249219982215908455[54] = 0.0;
   out_8249219982215908455[55] = 0.0;
   out_8249219982215908455[56] = 0.0;
   out_8249219982215908455[57] = 1.0;
   out_8249219982215908455[58] = 0.0;
   out_8249219982215908455[59] = 0.0;
   out_8249219982215908455[60] = 0.0;
   out_8249219982215908455[61] = 0.0;
   out_8249219982215908455[62] = 0.0;
   out_8249219982215908455[63] = 0.0;
   out_8249219982215908455[64] = 0.0;
   out_8249219982215908455[65] = 0.0;
   out_8249219982215908455[66] = 0.0;
   out_8249219982215908455[67] = 0.0;
   out_8249219982215908455[68] = 0.0;
   out_8249219982215908455[69] = 0.0;
   out_8249219982215908455[70] = 0.0;
   out_8249219982215908455[71] = 0.0;
   out_8249219982215908455[72] = 0.0;
   out_8249219982215908455[73] = 0.0;
   out_8249219982215908455[74] = 0.0;
   out_8249219982215908455[75] = 0.0;
   out_8249219982215908455[76] = 1.0;
   out_8249219982215908455[77] = 0.0;
   out_8249219982215908455[78] = 0.0;
   out_8249219982215908455[79] = 0.0;
   out_8249219982215908455[80] = 0.0;
   out_8249219982215908455[81] = 0.0;
   out_8249219982215908455[82] = 0.0;
   out_8249219982215908455[83] = 0.0;
   out_8249219982215908455[84] = 0.0;
   out_8249219982215908455[85] = 0.0;
   out_8249219982215908455[86] = 0.0;
   out_8249219982215908455[87] = 0.0;
   out_8249219982215908455[88] = 0.0;
   out_8249219982215908455[89] = 0.0;
   out_8249219982215908455[90] = 0.0;
   out_8249219982215908455[91] = 0.0;
   out_8249219982215908455[92] = 0.0;
   out_8249219982215908455[93] = 0.0;
   out_8249219982215908455[94] = 0.0;
   out_8249219982215908455[95] = 1.0;
   out_8249219982215908455[96] = 0.0;
   out_8249219982215908455[97] = 0.0;
   out_8249219982215908455[98] = 0.0;
   out_8249219982215908455[99] = 0.0;
   out_8249219982215908455[100] = 0.0;
   out_8249219982215908455[101] = 0.0;
   out_8249219982215908455[102] = 0.0;
   out_8249219982215908455[103] = 0.0;
   out_8249219982215908455[104] = 0.0;
   out_8249219982215908455[105] = 0.0;
   out_8249219982215908455[106] = 0.0;
   out_8249219982215908455[107] = 0.0;
   out_8249219982215908455[108] = 0.0;
   out_8249219982215908455[109] = 0.0;
   out_8249219982215908455[110] = 0.0;
   out_8249219982215908455[111] = 0.0;
   out_8249219982215908455[112] = 0.0;
   out_8249219982215908455[113] = 0.0;
   out_8249219982215908455[114] = 1.0;
   out_8249219982215908455[115] = 0.0;
   out_8249219982215908455[116] = 0.0;
   out_8249219982215908455[117] = 0.0;
   out_8249219982215908455[118] = 0.0;
   out_8249219982215908455[119] = 0.0;
   out_8249219982215908455[120] = 0.0;
   out_8249219982215908455[121] = 0.0;
   out_8249219982215908455[122] = 0.0;
   out_8249219982215908455[123] = 0.0;
   out_8249219982215908455[124] = 0.0;
   out_8249219982215908455[125] = 0.0;
   out_8249219982215908455[126] = 0.0;
   out_8249219982215908455[127] = 0.0;
   out_8249219982215908455[128] = 0.0;
   out_8249219982215908455[129] = 0.0;
   out_8249219982215908455[130] = 0.0;
   out_8249219982215908455[131] = 0.0;
   out_8249219982215908455[132] = 0.0;
   out_8249219982215908455[133] = 1.0;
   out_8249219982215908455[134] = 0.0;
   out_8249219982215908455[135] = 0.0;
   out_8249219982215908455[136] = 0.0;
   out_8249219982215908455[137] = 0.0;
   out_8249219982215908455[138] = 0.0;
   out_8249219982215908455[139] = 0.0;
   out_8249219982215908455[140] = 0.0;
   out_8249219982215908455[141] = 0.0;
   out_8249219982215908455[142] = 0.0;
   out_8249219982215908455[143] = 0.0;
   out_8249219982215908455[144] = 0.0;
   out_8249219982215908455[145] = 0.0;
   out_8249219982215908455[146] = 0.0;
   out_8249219982215908455[147] = 0.0;
   out_8249219982215908455[148] = 0.0;
   out_8249219982215908455[149] = 0.0;
   out_8249219982215908455[150] = 0.0;
   out_8249219982215908455[151] = 0.0;
   out_8249219982215908455[152] = 1.0;
   out_8249219982215908455[153] = 0.0;
   out_8249219982215908455[154] = 0.0;
   out_8249219982215908455[155] = 0.0;
   out_8249219982215908455[156] = 0.0;
   out_8249219982215908455[157] = 0.0;
   out_8249219982215908455[158] = 0.0;
   out_8249219982215908455[159] = 0.0;
   out_8249219982215908455[160] = 0.0;
   out_8249219982215908455[161] = 0.0;
   out_8249219982215908455[162] = 0.0;
   out_8249219982215908455[163] = 0.0;
   out_8249219982215908455[164] = 0.0;
   out_8249219982215908455[165] = 0.0;
   out_8249219982215908455[166] = 0.0;
   out_8249219982215908455[167] = 0.0;
   out_8249219982215908455[168] = 0.0;
   out_8249219982215908455[169] = 0.0;
   out_8249219982215908455[170] = 0.0;
   out_8249219982215908455[171] = 1.0;
   out_8249219982215908455[172] = 0.0;
   out_8249219982215908455[173] = 0.0;
   out_8249219982215908455[174] = 0.0;
   out_8249219982215908455[175] = 0.0;
   out_8249219982215908455[176] = 0.0;
   out_8249219982215908455[177] = 0.0;
   out_8249219982215908455[178] = 0.0;
   out_8249219982215908455[179] = 0.0;
   out_8249219982215908455[180] = 0.0;
   out_8249219982215908455[181] = 0.0;
   out_8249219982215908455[182] = 0.0;
   out_8249219982215908455[183] = 0.0;
   out_8249219982215908455[184] = 0.0;
   out_8249219982215908455[185] = 0.0;
   out_8249219982215908455[186] = 0.0;
   out_8249219982215908455[187] = 0.0;
   out_8249219982215908455[188] = 0.0;
   out_8249219982215908455[189] = 0.0;
   out_8249219982215908455[190] = 1.0;
   out_8249219982215908455[191] = 0.0;
   out_8249219982215908455[192] = 0.0;
   out_8249219982215908455[193] = 0.0;
   out_8249219982215908455[194] = 0.0;
   out_8249219982215908455[195] = 0.0;
   out_8249219982215908455[196] = 0.0;
   out_8249219982215908455[197] = 0.0;
   out_8249219982215908455[198] = 0.0;
   out_8249219982215908455[199] = 0.0;
   out_8249219982215908455[200] = 0.0;
   out_8249219982215908455[201] = 0.0;
   out_8249219982215908455[202] = 0.0;
   out_8249219982215908455[203] = 0.0;
   out_8249219982215908455[204] = 0.0;
   out_8249219982215908455[205] = 0.0;
   out_8249219982215908455[206] = 0.0;
   out_8249219982215908455[207] = 0.0;
   out_8249219982215908455[208] = 0.0;
   out_8249219982215908455[209] = 1.0;
   out_8249219982215908455[210] = 0.0;
   out_8249219982215908455[211] = 0.0;
   out_8249219982215908455[212] = 0.0;
   out_8249219982215908455[213] = 0.0;
   out_8249219982215908455[214] = 0.0;
   out_8249219982215908455[215] = 0.0;
   out_8249219982215908455[216] = 0.0;
   out_8249219982215908455[217] = 0.0;
   out_8249219982215908455[218] = 0.0;
   out_8249219982215908455[219] = 0.0;
   out_8249219982215908455[220] = 0.0;
   out_8249219982215908455[221] = 0.0;
   out_8249219982215908455[222] = 0.0;
   out_8249219982215908455[223] = 0.0;
   out_8249219982215908455[224] = 0.0;
   out_8249219982215908455[225] = 0.0;
   out_8249219982215908455[226] = 0.0;
   out_8249219982215908455[227] = 0.0;
   out_8249219982215908455[228] = 1.0;
   out_8249219982215908455[229] = 0.0;
   out_8249219982215908455[230] = 0.0;
   out_8249219982215908455[231] = 0.0;
   out_8249219982215908455[232] = 0.0;
   out_8249219982215908455[233] = 0.0;
   out_8249219982215908455[234] = 0.0;
   out_8249219982215908455[235] = 0.0;
   out_8249219982215908455[236] = 0.0;
   out_8249219982215908455[237] = 0.0;
   out_8249219982215908455[238] = 0.0;
   out_8249219982215908455[239] = 0.0;
   out_8249219982215908455[240] = 0.0;
   out_8249219982215908455[241] = 0.0;
   out_8249219982215908455[242] = 0.0;
   out_8249219982215908455[243] = 0.0;
   out_8249219982215908455[244] = 0.0;
   out_8249219982215908455[245] = 0.0;
   out_8249219982215908455[246] = 0.0;
   out_8249219982215908455[247] = 1.0;
   out_8249219982215908455[248] = 0.0;
   out_8249219982215908455[249] = 0.0;
   out_8249219982215908455[250] = 0.0;
   out_8249219982215908455[251] = 0.0;
   out_8249219982215908455[252] = 0.0;
   out_8249219982215908455[253] = 0.0;
   out_8249219982215908455[254] = 0.0;
   out_8249219982215908455[255] = 0.0;
   out_8249219982215908455[256] = 0.0;
   out_8249219982215908455[257] = 0.0;
   out_8249219982215908455[258] = 0.0;
   out_8249219982215908455[259] = 0.0;
   out_8249219982215908455[260] = 0.0;
   out_8249219982215908455[261] = 0.0;
   out_8249219982215908455[262] = 0.0;
   out_8249219982215908455[263] = 0.0;
   out_8249219982215908455[264] = 0.0;
   out_8249219982215908455[265] = 0.0;
   out_8249219982215908455[266] = 1.0;
   out_8249219982215908455[267] = 0.0;
   out_8249219982215908455[268] = 0.0;
   out_8249219982215908455[269] = 0.0;
   out_8249219982215908455[270] = 0.0;
   out_8249219982215908455[271] = 0.0;
   out_8249219982215908455[272] = 0.0;
   out_8249219982215908455[273] = 0.0;
   out_8249219982215908455[274] = 0.0;
   out_8249219982215908455[275] = 0.0;
   out_8249219982215908455[276] = 0.0;
   out_8249219982215908455[277] = 0.0;
   out_8249219982215908455[278] = 0.0;
   out_8249219982215908455[279] = 0.0;
   out_8249219982215908455[280] = 0.0;
   out_8249219982215908455[281] = 0.0;
   out_8249219982215908455[282] = 0.0;
   out_8249219982215908455[283] = 0.0;
   out_8249219982215908455[284] = 0.0;
   out_8249219982215908455[285] = 1.0;
   out_8249219982215908455[286] = 0.0;
   out_8249219982215908455[287] = 0.0;
   out_8249219982215908455[288] = 0.0;
   out_8249219982215908455[289] = 0.0;
   out_8249219982215908455[290] = 0.0;
   out_8249219982215908455[291] = 0.0;
   out_8249219982215908455[292] = 0.0;
   out_8249219982215908455[293] = 0.0;
   out_8249219982215908455[294] = 0.0;
   out_8249219982215908455[295] = 0.0;
   out_8249219982215908455[296] = 0.0;
   out_8249219982215908455[297] = 0.0;
   out_8249219982215908455[298] = 0.0;
   out_8249219982215908455[299] = 0.0;
   out_8249219982215908455[300] = 0.0;
   out_8249219982215908455[301] = 0.0;
   out_8249219982215908455[302] = 0.0;
   out_8249219982215908455[303] = 0.0;
   out_8249219982215908455[304] = 1.0;
   out_8249219982215908455[305] = 0.0;
   out_8249219982215908455[306] = 0.0;
   out_8249219982215908455[307] = 0.0;
   out_8249219982215908455[308] = 0.0;
   out_8249219982215908455[309] = 0.0;
   out_8249219982215908455[310] = 0.0;
   out_8249219982215908455[311] = 0.0;
   out_8249219982215908455[312] = 0.0;
   out_8249219982215908455[313] = 0.0;
   out_8249219982215908455[314] = 0.0;
   out_8249219982215908455[315] = 0.0;
   out_8249219982215908455[316] = 0.0;
   out_8249219982215908455[317] = 0.0;
   out_8249219982215908455[318] = 0.0;
   out_8249219982215908455[319] = 0.0;
   out_8249219982215908455[320] = 0.0;
   out_8249219982215908455[321] = 0.0;
   out_8249219982215908455[322] = 0.0;
   out_8249219982215908455[323] = 1.0;
}
void f_fun(double *state, double dt, double *out_741196485394149917) {
   out_741196485394149917[0] = atan2((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), -(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]));
   out_741196485394149917[1] = asin(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]));
   out_741196485394149917[2] = atan2(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), -(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]));
   out_741196485394149917[3] = dt*state[12] + state[3];
   out_741196485394149917[4] = dt*state[13] + state[4];
   out_741196485394149917[5] = dt*state[14] + state[5];
   out_741196485394149917[6] = state[6];
   out_741196485394149917[7] = state[7];
   out_741196485394149917[8] = state[8];
   out_741196485394149917[9] = state[9];
   out_741196485394149917[10] = state[10];
   out_741196485394149917[11] = state[11];
   out_741196485394149917[12] = state[12];
   out_741196485394149917[13] = state[13];
   out_741196485394149917[14] = state[14];
   out_741196485394149917[15] = state[15];
   out_741196485394149917[16] = state[16];
   out_741196485394149917[17] = state[17];
}
void F_fun(double *state, double dt, double *out_914245573923806659) {
   out_914245573923806659[0] = ((-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*cos(state[0])*cos(state[1]) - sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*cos(state[0])*cos(state[1]) - sin(dt*state[6])*sin(state[0])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_914245573923806659[1] = ((-sin(dt*state[6])*sin(dt*state[8]) - sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*cos(state[1]) - (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*sin(state[1]) - sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(state[0]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*sin(state[1]) + (-sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) + sin(dt*state[8])*cos(dt*state[6]))*cos(state[1]) - sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(state[0]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_914245573923806659[2] = 0;
   out_914245573923806659[3] = 0;
   out_914245573923806659[4] = 0;
   out_914245573923806659[5] = 0;
   out_914245573923806659[6] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(dt*cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) - dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_914245573923806659[7] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*sin(dt*state[7])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[6])*sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) - dt*sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[7])*cos(dt*state[6])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[8])*sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]) - dt*sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_914245573923806659[8] = ((dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((dt*sin(dt*state[6])*sin(dt*state[8]) + dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_914245573923806659[9] = 0;
   out_914245573923806659[10] = 0;
   out_914245573923806659[11] = 0;
   out_914245573923806659[12] = 0;
   out_914245573923806659[13] = 0;
   out_914245573923806659[14] = 0;
   out_914245573923806659[15] = 0;
   out_914245573923806659[16] = 0;
   out_914245573923806659[17] = 0;
   out_914245573923806659[18] = (-sin(dt*state[7])*sin(state[0])*cos(state[1]) - sin(dt*state[8])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_914245573923806659[19] = (-sin(dt*state[7])*sin(state[1])*cos(state[0]) + sin(dt*state[8])*sin(state[0])*sin(state[1])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_914245573923806659[20] = 0;
   out_914245573923806659[21] = 0;
   out_914245573923806659[22] = 0;
   out_914245573923806659[23] = 0;
   out_914245573923806659[24] = 0;
   out_914245573923806659[25] = (dt*sin(dt*state[7])*sin(dt*state[8])*sin(state[0])*cos(state[1]) - dt*sin(dt*state[7])*sin(state[1])*cos(dt*state[8]) + dt*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_914245573923806659[26] = (-dt*sin(dt*state[8])*sin(state[1])*cos(dt*state[7]) - dt*sin(state[0])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_914245573923806659[27] = 0;
   out_914245573923806659[28] = 0;
   out_914245573923806659[29] = 0;
   out_914245573923806659[30] = 0;
   out_914245573923806659[31] = 0;
   out_914245573923806659[32] = 0;
   out_914245573923806659[33] = 0;
   out_914245573923806659[34] = 0;
   out_914245573923806659[35] = 0;
   out_914245573923806659[36] = ((sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_914245573923806659[37] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-sin(dt*state[7])*sin(state[2])*cos(state[0])*cos(state[1]) + sin(dt*state[8])*sin(state[0])*sin(state[2])*cos(dt*state[7])*cos(state[1]) - sin(state[1])*sin(state[2])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(-sin(dt*state[7])*cos(state[0])*cos(state[1])*cos(state[2]) + sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1])*cos(state[2]) - sin(state[1])*cos(dt*state[7])*cos(dt*state[8])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_914245573923806659[38] = ((-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (-sin(state[0])*sin(state[1])*sin(state[2]) - cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_914245573923806659[39] = 0;
   out_914245573923806659[40] = 0;
   out_914245573923806659[41] = 0;
   out_914245573923806659[42] = 0;
   out_914245573923806659[43] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(dt*(sin(state[0])*cos(state[2]) - sin(state[1])*sin(state[2])*cos(state[0]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*sin(state[2])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(dt*(-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_914245573923806659[44] = (dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*sin(state[2])*cos(dt*state[7])*cos(state[1]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + (dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[7])*cos(state[1])*cos(state[2]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_914245573923806659[45] = 0;
   out_914245573923806659[46] = 0;
   out_914245573923806659[47] = 0;
   out_914245573923806659[48] = 0;
   out_914245573923806659[49] = 0;
   out_914245573923806659[50] = 0;
   out_914245573923806659[51] = 0;
   out_914245573923806659[52] = 0;
   out_914245573923806659[53] = 0;
   out_914245573923806659[54] = 0;
   out_914245573923806659[55] = 0;
   out_914245573923806659[56] = 0;
   out_914245573923806659[57] = 1;
   out_914245573923806659[58] = 0;
   out_914245573923806659[59] = 0;
   out_914245573923806659[60] = 0;
   out_914245573923806659[61] = 0;
   out_914245573923806659[62] = 0;
   out_914245573923806659[63] = 0;
   out_914245573923806659[64] = 0;
   out_914245573923806659[65] = 0;
   out_914245573923806659[66] = dt;
   out_914245573923806659[67] = 0;
   out_914245573923806659[68] = 0;
   out_914245573923806659[69] = 0;
   out_914245573923806659[70] = 0;
   out_914245573923806659[71] = 0;
   out_914245573923806659[72] = 0;
   out_914245573923806659[73] = 0;
   out_914245573923806659[74] = 0;
   out_914245573923806659[75] = 0;
   out_914245573923806659[76] = 1;
   out_914245573923806659[77] = 0;
   out_914245573923806659[78] = 0;
   out_914245573923806659[79] = 0;
   out_914245573923806659[80] = 0;
   out_914245573923806659[81] = 0;
   out_914245573923806659[82] = 0;
   out_914245573923806659[83] = 0;
   out_914245573923806659[84] = 0;
   out_914245573923806659[85] = dt;
   out_914245573923806659[86] = 0;
   out_914245573923806659[87] = 0;
   out_914245573923806659[88] = 0;
   out_914245573923806659[89] = 0;
   out_914245573923806659[90] = 0;
   out_914245573923806659[91] = 0;
   out_914245573923806659[92] = 0;
   out_914245573923806659[93] = 0;
   out_914245573923806659[94] = 0;
   out_914245573923806659[95] = 1;
   out_914245573923806659[96] = 0;
   out_914245573923806659[97] = 0;
   out_914245573923806659[98] = 0;
   out_914245573923806659[99] = 0;
   out_914245573923806659[100] = 0;
   out_914245573923806659[101] = 0;
   out_914245573923806659[102] = 0;
   out_914245573923806659[103] = 0;
   out_914245573923806659[104] = dt;
   out_914245573923806659[105] = 0;
   out_914245573923806659[106] = 0;
   out_914245573923806659[107] = 0;
   out_914245573923806659[108] = 0;
   out_914245573923806659[109] = 0;
   out_914245573923806659[110] = 0;
   out_914245573923806659[111] = 0;
   out_914245573923806659[112] = 0;
   out_914245573923806659[113] = 0;
   out_914245573923806659[114] = 1;
   out_914245573923806659[115] = 0;
   out_914245573923806659[116] = 0;
   out_914245573923806659[117] = 0;
   out_914245573923806659[118] = 0;
   out_914245573923806659[119] = 0;
   out_914245573923806659[120] = 0;
   out_914245573923806659[121] = 0;
   out_914245573923806659[122] = 0;
   out_914245573923806659[123] = 0;
   out_914245573923806659[124] = 0;
   out_914245573923806659[125] = 0;
   out_914245573923806659[126] = 0;
   out_914245573923806659[127] = 0;
   out_914245573923806659[128] = 0;
   out_914245573923806659[129] = 0;
   out_914245573923806659[130] = 0;
   out_914245573923806659[131] = 0;
   out_914245573923806659[132] = 0;
   out_914245573923806659[133] = 1;
   out_914245573923806659[134] = 0;
   out_914245573923806659[135] = 0;
   out_914245573923806659[136] = 0;
   out_914245573923806659[137] = 0;
   out_914245573923806659[138] = 0;
   out_914245573923806659[139] = 0;
   out_914245573923806659[140] = 0;
   out_914245573923806659[141] = 0;
   out_914245573923806659[142] = 0;
   out_914245573923806659[143] = 0;
   out_914245573923806659[144] = 0;
   out_914245573923806659[145] = 0;
   out_914245573923806659[146] = 0;
   out_914245573923806659[147] = 0;
   out_914245573923806659[148] = 0;
   out_914245573923806659[149] = 0;
   out_914245573923806659[150] = 0;
   out_914245573923806659[151] = 0;
   out_914245573923806659[152] = 1;
   out_914245573923806659[153] = 0;
   out_914245573923806659[154] = 0;
   out_914245573923806659[155] = 0;
   out_914245573923806659[156] = 0;
   out_914245573923806659[157] = 0;
   out_914245573923806659[158] = 0;
   out_914245573923806659[159] = 0;
   out_914245573923806659[160] = 0;
   out_914245573923806659[161] = 0;
   out_914245573923806659[162] = 0;
   out_914245573923806659[163] = 0;
   out_914245573923806659[164] = 0;
   out_914245573923806659[165] = 0;
   out_914245573923806659[166] = 0;
   out_914245573923806659[167] = 0;
   out_914245573923806659[168] = 0;
   out_914245573923806659[169] = 0;
   out_914245573923806659[170] = 0;
   out_914245573923806659[171] = 1;
   out_914245573923806659[172] = 0;
   out_914245573923806659[173] = 0;
   out_914245573923806659[174] = 0;
   out_914245573923806659[175] = 0;
   out_914245573923806659[176] = 0;
   out_914245573923806659[177] = 0;
   out_914245573923806659[178] = 0;
   out_914245573923806659[179] = 0;
   out_914245573923806659[180] = 0;
   out_914245573923806659[181] = 0;
   out_914245573923806659[182] = 0;
   out_914245573923806659[183] = 0;
   out_914245573923806659[184] = 0;
   out_914245573923806659[185] = 0;
   out_914245573923806659[186] = 0;
   out_914245573923806659[187] = 0;
   out_914245573923806659[188] = 0;
   out_914245573923806659[189] = 0;
   out_914245573923806659[190] = 1;
   out_914245573923806659[191] = 0;
   out_914245573923806659[192] = 0;
   out_914245573923806659[193] = 0;
   out_914245573923806659[194] = 0;
   out_914245573923806659[195] = 0;
   out_914245573923806659[196] = 0;
   out_914245573923806659[197] = 0;
   out_914245573923806659[198] = 0;
   out_914245573923806659[199] = 0;
   out_914245573923806659[200] = 0;
   out_914245573923806659[201] = 0;
   out_914245573923806659[202] = 0;
   out_914245573923806659[203] = 0;
   out_914245573923806659[204] = 0;
   out_914245573923806659[205] = 0;
   out_914245573923806659[206] = 0;
   out_914245573923806659[207] = 0;
   out_914245573923806659[208] = 0;
   out_914245573923806659[209] = 1;
   out_914245573923806659[210] = 0;
   out_914245573923806659[211] = 0;
   out_914245573923806659[212] = 0;
   out_914245573923806659[213] = 0;
   out_914245573923806659[214] = 0;
   out_914245573923806659[215] = 0;
   out_914245573923806659[216] = 0;
   out_914245573923806659[217] = 0;
   out_914245573923806659[218] = 0;
   out_914245573923806659[219] = 0;
   out_914245573923806659[220] = 0;
   out_914245573923806659[221] = 0;
   out_914245573923806659[222] = 0;
   out_914245573923806659[223] = 0;
   out_914245573923806659[224] = 0;
   out_914245573923806659[225] = 0;
   out_914245573923806659[226] = 0;
   out_914245573923806659[227] = 0;
   out_914245573923806659[228] = 1;
   out_914245573923806659[229] = 0;
   out_914245573923806659[230] = 0;
   out_914245573923806659[231] = 0;
   out_914245573923806659[232] = 0;
   out_914245573923806659[233] = 0;
   out_914245573923806659[234] = 0;
   out_914245573923806659[235] = 0;
   out_914245573923806659[236] = 0;
   out_914245573923806659[237] = 0;
   out_914245573923806659[238] = 0;
   out_914245573923806659[239] = 0;
   out_914245573923806659[240] = 0;
   out_914245573923806659[241] = 0;
   out_914245573923806659[242] = 0;
   out_914245573923806659[243] = 0;
   out_914245573923806659[244] = 0;
   out_914245573923806659[245] = 0;
   out_914245573923806659[246] = 0;
   out_914245573923806659[247] = 1;
   out_914245573923806659[248] = 0;
   out_914245573923806659[249] = 0;
   out_914245573923806659[250] = 0;
   out_914245573923806659[251] = 0;
   out_914245573923806659[252] = 0;
   out_914245573923806659[253] = 0;
   out_914245573923806659[254] = 0;
   out_914245573923806659[255] = 0;
   out_914245573923806659[256] = 0;
   out_914245573923806659[257] = 0;
   out_914245573923806659[258] = 0;
   out_914245573923806659[259] = 0;
   out_914245573923806659[260] = 0;
   out_914245573923806659[261] = 0;
   out_914245573923806659[262] = 0;
   out_914245573923806659[263] = 0;
   out_914245573923806659[264] = 0;
   out_914245573923806659[265] = 0;
   out_914245573923806659[266] = 1;
   out_914245573923806659[267] = 0;
   out_914245573923806659[268] = 0;
   out_914245573923806659[269] = 0;
   out_914245573923806659[270] = 0;
   out_914245573923806659[271] = 0;
   out_914245573923806659[272] = 0;
   out_914245573923806659[273] = 0;
   out_914245573923806659[274] = 0;
   out_914245573923806659[275] = 0;
   out_914245573923806659[276] = 0;
   out_914245573923806659[277] = 0;
   out_914245573923806659[278] = 0;
   out_914245573923806659[279] = 0;
   out_914245573923806659[280] = 0;
   out_914245573923806659[281] = 0;
   out_914245573923806659[282] = 0;
   out_914245573923806659[283] = 0;
   out_914245573923806659[284] = 0;
   out_914245573923806659[285] = 1;
   out_914245573923806659[286] = 0;
   out_914245573923806659[287] = 0;
   out_914245573923806659[288] = 0;
   out_914245573923806659[289] = 0;
   out_914245573923806659[290] = 0;
   out_914245573923806659[291] = 0;
   out_914245573923806659[292] = 0;
   out_914245573923806659[293] = 0;
   out_914245573923806659[294] = 0;
   out_914245573923806659[295] = 0;
   out_914245573923806659[296] = 0;
   out_914245573923806659[297] = 0;
   out_914245573923806659[298] = 0;
   out_914245573923806659[299] = 0;
   out_914245573923806659[300] = 0;
   out_914245573923806659[301] = 0;
   out_914245573923806659[302] = 0;
   out_914245573923806659[303] = 0;
   out_914245573923806659[304] = 1;
   out_914245573923806659[305] = 0;
   out_914245573923806659[306] = 0;
   out_914245573923806659[307] = 0;
   out_914245573923806659[308] = 0;
   out_914245573923806659[309] = 0;
   out_914245573923806659[310] = 0;
   out_914245573923806659[311] = 0;
   out_914245573923806659[312] = 0;
   out_914245573923806659[313] = 0;
   out_914245573923806659[314] = 0;
   out_914245573923806659[315] = 0;
   out_914245573923806659[316] = 0;
   out_914245573923806659[317] = 0;
   out_914245573923806659[318] = 0;
   out_914245573923806659[319] = 0;
   out_914245573923806659[320] = 0;
   out_914245573923806659[321] = 0;
   out_914245573923806659[322] = 0;
   out_914245573923806659[323] = 1;
}
void h_4(double *state, double *unused, double *out_1661592600804563205) {
   out_1661592600804563205[0] = state[6] + state[9];
   out_1661592600804563205[1] = state[7] + state[10];
   out_1661592600804563205[2] = state[8] + state[11];
}
void H_4(double *state, double *unused, double *out_3634592945286592091) {
   out_3634592945286592091[0] = 0;
   out_3634592945286592091[1] = 0;
   out_3634592945286592091[2] = 0;
   out_3634592945286592091[3] = 0;
   out_3634592945286592091[4] = 0;
   out_3634592945286592091[5] = 0;
   out_3634592945286592091[6] = 1;
   out_3634592945286592091[7] = 0;
   out_3634592945286592091[8] = 0;
   out_3634592945286592091[9] = 1;
   out_3634592945286592091[10] = 0;
   out_3634592945286592091[11] = 0;
   out_3634592945286592091[12] = 0;
   out_3634592945286592091[13] = 0;
   out_3634592945286592091[14] = 0;
   out_3634592945286592091[15] = 0;
   out_3634592945286592091[16] = 0;
   out_3634592945286592091[17] = 0;
   out_3634592945286592091[18] = 0;
   out_3634592945286592091[19] = 0;
   out_3634592945286592091[20] = 0;
   out_3634592945286592091[21] = 0;
   out_3634592945286592091[22] = 0;
   out_3634592945286592091[23] = 0;
   out_3634592945286592091[24] = 0;
   out_3634592945286592091[25] = 1;
   out_3634592945286592091[26] = 0;
   out_3634592945286592091[27] = 0;
   out_3634592945286592091[28] = 1;
   out_3634592945286592091[29] = 0;
   out_3634592945286592091[30] = 0;
   out_3634592945286592091[31] = 0;
   out_3634592945286592091[32] = 0;
   out_3634592945286592091[33] = 0;
   out_3634592945286592091[34] = 0;
   out_3634592945286592091[35] = 0;
   out_3634592945286592091[36] = 0;
   out_3634592945286592091[37] = 0;
   out_3634592945286592091[38] = 0;
   out_3634592945286592091[39] = 0;
   out_3634592945286592091[40] = 0;
   out_3634592945286592091[41] = 0;
   out_3634592945286592091[42] = 0;
   out_3634592945286592091[43] = 0;
   out_3634592945286592091[44] = 1;
   out_3634592945286592091[45] = 0;
   out_3634592945286592091[46] = 0;
   out_3634592945286592091[47] = 1;
   out_3634592945286592091[48] = 0;
   out_3634592945286592091[49] = 0;
   out_3634592945286592091[50] = 0;
   out_3634592945286592091[51] = 0;
   out_3634592945286592091[52] = 0;
   out_3634592945286592091[53] = 0;
}
void h_10(double *state, double *unused, double *out_1540829144479980375) {
   out_1540829144479980375[0] = 9.8100000000000005*sin(state[1]) - state[4]*state[8] + state[5]*state[7] + state[12] + state[15];
   out_1540829144479980375[1] = -9.8100000000000005*sin(state[0])*cos(state[1]) + state[3]*state[8] - state[5]*state[6] + state[13] + state[16];
   out_1540829144479980375[2] = -9.8100000000000005*cos(state[0])*cos(state[1]) - state[3]*state[7] + state[4]*state[6] + state[14] + state[17];
}
void H_10(double *state, double *unused, double *out_3859318150895892325) {
   out_3859318150895892325[0] = 0;
   out_3859318150895892325[1] = 9.8100000000000005*cos(state[1]);
   out_3859318150895892325[2] = 0;
   out_3859318150895892325[3] = 0;
   out_3859318150895892325[4] = -state[8];
   out_3859318150895892325[5] = state[7];
   out_3859318150895892325[6] = 0;
   out_3859318150895892325[7] = state[5];
   out_3859318150895892325[8] = -state[4];
   out_3859318150895892325[9] = 0;
   out_3859318150895892325[10] = 0;
   out_3859318150895892325[11] = 0;
   out_3859318150895892325[12] = 1;
   out_3859318150895892325[13] = 0;
   out_3859318150895892325[14] = 0;
   out_3859318150895892325[15] = 1;
   out_3859318150895892325[16] = 0;
   out_3859318150895892325[17] = 0;
   out_3859318150895892325[18] = -9.8100000000000005*cos(state[0])*cos(state[1]);
   out_3859318150895892325[19] = 9.8100000000000005*sin(state[0])*sin(state[1]);
   out_3859318150895892325[20] = 0;
   out_3859318150895892325[21] = state[8];
   out_3859318150895892325[22] = 0;
   out_3859318150895892325[23] = -state[6];
   out_3859318150895892325[24] = -state[5];
   out_3859318150895892325[25] = 0;
   out_3859318150895892325[26] = state[3];
   out_3859318150895892325[27] = 0;
   out_3859318150895892325[28] = 0;
   out_3859318150895892325[29] = 0;
   out_3859318150895892325[30] = 0;
   out_3859318150895892325[31] = 1;
   out_3859318150895892325[32] = 0;
   out_3859318150895892325[33] = 0;
   out_3859318150895892325[34] = 1;
   out_3859318150895892325[35] = 0;
   out_3859318150895892325[36] = 9.8100000000000005*sin(state[0])*cos(state[1]);
   out_3859318150895892325[37] = 9.8100000000000005*sin(state[1])*cos(state[0]);
   out_3859318150895892325[38] = 0;
   out_3859318150895892325[39] = -state[7];
   out_3859318150895892325[40] = state[6];
   out_3859318150895892325[41] = 0;
   out_3859318150895892325[42] = state[4];
   out_3859318150895892325[43] = -state[3];
   out_3859318150895892325[44] = 0;
   out_3859318150895892325[45] = 0;
   out_3859318150895892325[46] = 0;
   out_3859318150895892325[47] = 0;
   out_3859318150895892325[48] = 0;
   out_3859318150895892325[49] = 0;
   out_3859318150895892325[50] = 1;
   out_3859318150895892325[51] = 0;
   out_3859318150895892325[52] = 0;
   out_3859318150895892325[53] = 1;
}
void h_13(double *state, double *unused, double *out_1494548337638663963) {
   out_1494548337638663963[0] = state[3];
   out_1494548337638663963[1] = state[4];
   out_1494548337638663963[2] = state[5];
}
void H_13(double *state, double *unused, double *out_422319119954259290) {
   out_422319119954259290[0] = 0;
   out_422319119954259290[1] = 0;
   out_422319119954259290[2] = 0;
   out_422319119954259290[3] = 1;
   out_422319119954259290[4] = 0;
   out_422319119954259290[5] = 0;
   out_422319119954259290[6] = 0;
   out_422319119954259290[7] = 0;
   out_422319119954259290[8] = 0;
   out_422319119954259290[9] = 0;
   out_422319119954259290[10] = 0;
   out_422319119954259290[11] = 0;
   out_422319119954259290[12] = 0;
   out_422319119954259290[13] = 0;
   out_422319119954259290[14] = 0;
   out_422319119954259290[15] = 0;
   out_422319119954259290[16] = 0;
   out_422319119954259290[17] = 0;
   out_422319119954259290[18] = 0;
   out_422319119954259290[19] = 0;
   out_422319119954259290[20] = 0;
   out_422319119954259290[21] = 0;
   out_422319119954259290[22] = 1;
   out_422319119954259290[23] = 0;
   out_422319119954259290[24] = 0;
   out_422319119954259290[25] = 0;
   out_422319119954259290[26] = 0;
   out_422319119954259290[27] = 0;
   out_422319119954259290[28] = 0;
   out_422319119954259290[29] = 0;
   out_422319119954259290[30] = 0;
   out_422319119954259290[31] = 0;
   out_422319119954259290[32] = 0;
   out_422319119954259290[33] = 0;
   out_422319119954259290[34] = 0;
   out_422319119954259290[35] = 0;
   out_422319119954259290[36] = 0;
   out_422319119954259290[37] = 0;
   out_422319119954259290[38] = 0;
   out_422319119954259290[39] = 0;
   out_422319119954259290[40] = 0;
   out_422319119954259290[41] = 1;
   out_422319119954259290[42] = 0;
   out_422319119954259290[43] = 0;
   out_422319119954259290[44] = 0;
   out_422319119954259290[45] = 0;
   out_422319119954259290[46] = 0;
   out_422319119954259290[47] = 0;
   out_422319119954259290[48] = 0;
   out_422319119954259290[49] = 0;
   out_422319119954259290[50] = 0;
   out_422319119954259290[51] = 0;
   out_422319119954259290[52] = 0;
   out_422319119954259290[53] = 0;
}
void h_14(double *state, double *unused, double *out_4998597365434596125) {
   out_4998597365434596125[0] = state[6];
   out_4998597365434596125[1] = state[7];
   out_4998597365434596125[2] = state[8];
}
void H_14(double *state, double *unused, double *out_328647911052892438) {
   out_328647911052892438[0] = 0;
   out_328647911052892438[1] = 0;
   out_328647911052892438[2] = 0;
   out_328647911052892438[3] = 0;
   out_328647911052892438[4] = 0;
   out_328647911052892438[5] = 0;
   out_328647911052892438[6] = 1;
   out_328647911052892438[7] = 0;
   out_328647911052892438[8] = 0;
   out_328647911052892438[9] = 0;
   out_328647911052892438[10] = 0;
   out_328647911052892438[11] = 0;
   out_328647911052892438[12] = 0;
   out_328647911052892438[13] = 0;
   out_328647911052892438[14] = 0;
   out_328647911052892438[15] = 0;
   out_328647911052892438[16] = 0;
   out_328647911052892438[17] = 0;
   out_328647911052892438[18] = 0;
   out_328647911052892438[19] = 0;
   out_328647911052892438[20] = 0;
   out_328647911052892438[21] = 0;
   out_328647911052892438[22] = 0;
   out_328647911052892438[23] = 0;
   out_328647911052892438[24] = 0;
   out_328647911052892438[25] = 1;
   out_328647911052892438[26] = 0;
   out_328647911052892438[27] = 0;
   out_328647911052892438[28] = 0;
   out_328647911052892438[29] = 0;
   out_328647911052892438[30] = 0;
   out_328647911052892438[31] = 0;
   out_328647911052892438[32] = 0;
   out_328647911052892438[33] = 0;
   out_328647911052892438[34] = 0;
   out_328647911052892438[35] = 0;
   out_328647911052892438[36] = 0;
   out_328647911052892438[37] = 0;
   out_328647911052892438[38] = 0;
   out_328647911052892438[39] = 0;
   out_328647911052892438[40] = 0;
   out_328647911052892438[41] = 0;
   out_328647911052892438[42] = 0;
   out_328647911052892438[43] = 0;
   out_328647911052892438[44] = 1;
   out_328647911052892438[45] = 0;
   out_328647911052892438[46] = 0;
   out_328647911052892438[47] = 0;
   out_328647911052892438[48] = 0;
   out_328647911052892438[49] = 0;
   out_328647911052892438[50] = 0;
   out_328647911052892438[51] = 0;
   out_328647911052892438[52] = 0;
   out_328647911052892438[53] = 0;
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
void pose_err_fun(double *nom_x, double *delta_x, double *out_7675941765646048454) {
  err_fun(nom_x, delta_x, out_7675941765646048454);
}
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_6578985106349638079) {
  inv_err_fun(nom_x, true_x, out_6578985106349638079);
}
void pose_H_mod_fun(double *state, double *out_8249219982215908455) {
  H_mod_fun(state, out_8249219982215908455);
}
void pose_f_fun(double *state, double dt, double *out_741196485394149917) {
  f_fun(state,  dt, out_741196485394149917);
}
void pose_F_fun(double *state, double dt, double *out_914245573923806659) {
  F_fun(state,  dt, out_914245573923806659);
}
void pose_h_4(double *state, double *unused, double *out_1661592600804563205) {
  h_4(state, unused, out_1661592600804563205);
}
void pose_H_4(double *state, double *unused, double *out_3634592945286592091) {
  H_4(state, unused, out_3634592945286592091);
}
void pose_h_10(double *state, double *unused, double *out_1540829144479980375) {
  h_10(state, unused, out_1540829144479980375);
}
void pose_H_10(double *state, double *unused, double *out_3859318150895892325) {
  H_10(state, unused, out_3859318150895892325);
}
void pose_h_13(double *state, double *unused, double *out_1494548337638663963) {
  h_13(state, unused, out_1494548337638663963);
}
void pose_H_13(double *state, double *unused, double *out_422319119954259290) {
  H_13(state, unused, out_422319119954259290);
}
void pose_h_14(double *state, double *unused, double *out_4998597365434596125) {
  h_14(state, unused, out_4998597365434596125);
}
void pose_H_14(double *state, double *unused, double *out_328647911052892438) {
  H_14(state, unused, out_328647911052892438);
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
